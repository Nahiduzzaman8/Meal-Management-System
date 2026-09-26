# Meal Management System

![Python](https://img.shields.io/badge/python-3.13-blue)
![Django](https://img.shields.io/badge/django-5.x-green)
![DRF](https://img.shields.io/badge/DRF-3.15-red)
![License](https://img.shields.io/badge/license-MIT-lightgrey)
![Build](https://img.shields.io/badge/build-passing-brightgreen)

A single-mess meal, deposit, and expense accounting system for a shared
bachelor mess — built as a portfolio project.

> **A note on this document:** this README was assembled from the project's
> design specification and everything confirmed during end-to-end testing,
> not from a live scan of the repository. Sections marked **(verify)** should
> be checked against your actual `serializers.py`/`models.py` files — field
> names or defaults may have drifted slightly during implementation.

---

## Table of contents

1. [Overview](#overview)
2. [Tech stack](#tech-stack)
3. [Features](#features)
4. [Prerequisites](#prerequisites)
5. [Installation & setup](#installation--setup)
6. [Running the project](#running-the-project)
7. [Project structure](#project-structure)
8. [Authentication & authorization](#authentication--authorization)
9. [Core business rules](#core-business-rules)
10. [API reference](#api-reference)
11. [Deployment](#deployment)
12. [Testing](#testing)
13. [License](#license)
14. [Author](#author)

---

## Overview

The Meal Management System runs the full monthly accounting cycle for one
shared bachelor mess: members log daily meals, submit deposits, request
guest meals for visitors, and a rotating Manager approves transactions and
records expenses. At month end, the system computes a meal rate from total
expenses and total meals consumed, and settles each member's balance —
carrying any unpaid amount forward into the next month.

A few design decisions make this more than a basic CRUD app:

- **Three-state month lifecycle** (`PLANNED` → `OPEN` → `CLOSED`), not two.
  Members submit meals for *tomorrow*, so the next month must be creatable
  and able to accept meal data before the current one closes — without
  breaking the rule that only one month may be financially "open" at a time.
- **Balances carry forward.** A member's unpaid due at month-close becomes
  their opening balance the following month, so the ledger is continuous
  rather than resetting every 30 days.
- **Capability-based permissions, not role-based.** "Manager" is never a
  stored role — it's derived per-request from whether a member currently
  holds an active `ManagerAssignment` on the open month. This avoids a
  stale permission surviving after a manager handoff mid-month.
- **Corrections are ledger entries, not edits.** An approved deposit or
  guest meal is never mutated after approval — it's corrected with an
  `Adjustment` (debit or credit), keeping every approved record exactly as
  it was approved.
- **Exact reconciliation.** Meal rates are computed to 4 decimal places
  internally; member costs round to 2 decimals; the rounding remainder is
  explicitly allocated as an adjustment so the sum of every member's cost
  always equals total expenses exactly — never off by a few poysha.

---

## Tech stack

| Layer | Technology |
|---|---|
| Backend framework | Django 5.x |
| API layer | Django REST Framework |
| Authentication | djangorestframework-simplejwt (JWT, rotating refresh + blacklist) |
| Database (dev) | SQLite3 |
| Database (prod, optional) | PostgreSQL via `dj-database-url` — same code, swap `DATABASE_URL` |
| Frontend | React (separate repository/deployment) |
| CORS | django-cors-headers |
| Production server | gunicorn + whitenoise |

**(verify)** — confirm exact pinned versions in `requirements.txt` and update
the badges above if they differ from Django 5.x / DRF 3.15.

---

## Features

- **Authentication** — JWT login/refresh/logout, forced password change on
  first login, Admin-triggered password reset.
- **User management** — Admin-only user creation (auto-generated temporary
  password), deactivation/reactivation, immutable usernames.
- **Month management** — create, open (roster snapshot + balance
  carry-forward), close (calculation engine + validation), manager
  assignment.
- **Meal management** — daily lunch/dinner submission with a configurable
  cutoff deadline, upsert semantics.
- **Guest meals** — request with lunch/dinner quantities, Manager
  approve/reject, resubmission allowed after rejection.
- **Deposits** — submit with payment method and reference, Manager
  approve/reject.
- **Expenses** — categorized entries against the open month, soft delete
  with mandatory reason.
- **Adjustments** — Admin-only manual debit/credit corrections, also used
  automatically for rounding-residual allocation at month close.
- **Dashboard** — capability-shaped composite view (Member/Manager/Admin
  see different slices of the same data).
- **Reports** — monthly totals, member-wise breakdowns, balance history —
  explicitly labeled ESTIMATED (open month) or FINAL (closed month).
- **Audit log** — append-only action history, Admin-only read access.

---

## Prerequisites

- Python 3.13 (or 3.11+ — **(verify)** against your actual environment)
- pip
- `venv` (standard library, no separate install needed)

---

## Installation & setup

```bash
git clone <repo-url>
cd meal-management-system
python -m venv venv
source venv/bin/activate      # venv\Scripts\activate on Windows
pip install -r requirements.txt
```

Create a `.env` file at the project root:

```env
SECRET_KEY=your-secret-key-here
DEBUG=True
DATABASE_URL=sqlite:///db.sqlite3
```

**(verify)** — confirm this matches exactly what `config/settings.py` reads
via `python-decouple`; add any additional variables (e.g.
`CORS_ALLOWED_ORIGINS`) actually referenced there.

Run migrations:

```bash
python manage.py migrate
```

Create the first Admin account — **this is the only way an Admin account
can ever be created; there is no registration API for it:**

```bash
python manage.py create_admin
```

There is no self-registration anywhere in this system. Every Member account
is created by an Admin via `POST /api/users/` (see [API reference](#api-reference)).

---

## Running the project

```bash
python manage.py runserver
```

Run the full test suite:

```bash
python manage.py test apps
```

Run the single most important test — the full monthly cycle exercised
end-to-end through real HTTP calls:

```bash
python manage.py test apps.months.tests.test_full_workflow -v 2
```

---

## Project structure

```
meal-management-system/
├── config/                 # Django project settings, root urls.py
├── apps/
│   ├── users/               # User model, JWT auth, capability permissions,
│   │                        # create_admin command, Admin user-management API
│   ├── months/               # Month lifecycle, ManagerAssignment, MonthMember
│   │                        # roster/snapshot, calculation engine
│   ├── meals/                # Daily lunch/dinner submission
│   ├── guest_meals/           # Guest meal requests + approval workflow
│   ├── deposits/             # Member deposits + approval workflow
│   ├── expenses/             # Mess expenses, soft delete
│   ├── adjustments/          # Manual debit/credit corrections
│   ├── settings_app/          # Singleton SystemSetting (deadline, timezone, currency)
│   └── audit/                # Append-only AuditLog
├── requirements.txt
├── manage.py
└── README.md
```

**(verify)** — this reflects the apps scaffolded in the build stages; confirm
against your actual `apps/` directory in case any app was renamed.

---

## Authentication & authorization

### JWT flow

- **Access token:** 30 minutes
- **Refresh token:** 7 days, rotates on every use, old token blacklisted
- Deactivating a user blacklists all of their outstanding refresh tokens
  immediately

**(verify)** these lifetimes against `SIMPLE_JWT` in `config/settings.py` —
they were the values specified during build, confirm nothing was changed.

### `must_change_password` gate

Every new account (created by an Admin, or after an Admin-triggered reset)
has `must_change_password=True`. While set, every endpoint except
`GET /api/auth/me/`, `POST /api/auth/password/change/`, and
`POST /api/auth/logout/` returns:

```json
{ "code": "password_change_required", "message": "..." }
```

### Capability-based permissions

Permissions are checked against a plain Python dictionary — not
database-seeded role/permission tables:

```python
# apps/users/permissions.py
ROLE_CAPABILITIES = {
    "ADMIN": {
        "month.create", "month.open", "month.close",
        "manager.assign",
        "user.create", "user.view", "user.deactivate", "user.reset_password",
        "settings.manage", "adjustment.create", "audit.view",
    },
    "MEMBER": {
        "meal.submit", "meal.view_own",
        "deposit.submit", "deposit.view_own",
        "guest_meal.submit", "guest_meal.view_own",
        "report.view_own",
    },
}

# Added on top of base MEMBER capabilities for whoever holds the active
# ManagerAssignment on the currently OPEN month:
MANAGER_CAPABILITIES = {
    "meal.view_all",
    "deposit.approve",
    "guest_meal.approve",
    "expense.create", "expense.update", "expense.delete",
    "report.view_all",
}
```

**Manager is never a stored role.** `User.role` is only `ADMIN` or `MEMBER`.
Manager status is derived per-request from `ManagerAssignment` on the open
month, so a reassignment mid-month takes effect immediately, with no stale
token or cached claim to invalidate.

---

## Core business rules

**Meal units.** One lunch or one dinner for one person is one unit; a day
with both is two. Countable meal units = member meal units + *approved*
guest meal units — member meals carry no approval status, only guest meals
do.

**Month lifecycle.** Three states — `PLANNED`, `OPEN`, `CLOSED` — because
members submit meals for tomorrow, and a two-state system would deadlock on
the last evening of every month. Only one month may be `OPEN` at a time
(enforced with a partial `UniqueConstraint`, which works on SQLite as well
as PostgreSQL). Any number may be `PLANNED`.

**Balance carry-forward.** `closing_balance = opening_balance + total_cost +
adjustment_total − approved_deposit_total`. Positive means the member owes
the mess. The next month's `opening_balance` is exactly this month's
`closing_balance`.

**Rounding.** Rates are stored at 4 decimal places; member-facing costs
round half-up to 2. The remainder after rounding every member's cost is
posted as an `Adjustment` to the member with the highest meal-unit count
that month (ties broken by lowest member id) — so total member costs always
equal total expenses exactly.

**Corrections via Adjustment, never edits.** An approved deposit, an
approved guest meal, or the rounding residual is corrected with a `DEBIT`/
`CREDIT` Adjustment and a mandatory reason — never by mutating the original
approved record.

---

## API reference

All endpoints are resource-oriented (one route per resource); visibility is
enforced by filtering querysets against the caller's capabilities, not by
role-prefixed URLs. Every error response includes a machine-readable
`code` field alongside its message.

**(verify)** — the request/response shapes below reflect the design
specification and fields confirmed during testing (Expense fields were
directly confirmed from `serializers.py`). Cross-check every table against
your actual serializers before treating this as ground truth, especially
field names and required/optional status.

### Summary

| Method | Path | Capability | Description |
|---|---|---|---|
| POST | `/api/auth/login/` | public | Login, returns access + refresh + user |
| POST | `/api/auth/refresh/` | public | Rotates refresh token |
| POST | `/api/auth/logout/` | authenticated | Blacklists refresh token |
| GET | `/api/auth/me/` | authenticated | Profile + resolved capability list |
| POST | `/api/auth/password/change/` | authenticated | Clears must_change_password |
| GET | `/api/users/` | `user.view` | List users, filterable |
| POST | `/api/users/` | `user.create` | Create Member, returns one-time temp password |
| GET | `/api/users/{id}/` | `user.view` | User detail |
| POST | `/api/users/{id}/deactivate/` | `user.deactivate` | Deactivate (blocked if active manager) |
| POST | `/api/users/{id}/reactivate/` | `user.deactivate` | Reactivate |
| POST | `/api/users/{id}/reset-password/` | `user.reset_password` | New temp password, re-arms gate |
| POST | `/api/months/` | `month.create` | Create month (status=PLANNED) |
| POST | `/api/months/{id}/open/` | `month.open` | Open month, roster + carry-forward |
| POST | `/api/months/{id}/close/` | `month.close` | Close, run calculation engine |
| GET | `/api/months/{id}/members/` | `month.view` | Roster or frozen result |
| PUT | `/api/months/{id}/manager/` | `manager.assign` | Assign/reassign Manager |
| GET | `/api/meals/` | `meal.view_own` / `meal.view_all` | List meals |
| POST | `/api/meals/` | `meal.submit` | Upsert today's/tomorrow's meal |
| GET | `/api/guest-meals/` | `guest_meal.view_own` / `guest_meal.approve` | List guest meal requests |
| POST | `/api/guest-meals/` | `guest_meal.submit` | Request a guest meal |
| POST | `/api/guest-meals/{id}/approve/` | `guest_meal.approve` | Approve |
| POST | `/api/guest-meals/{id}/reject/` | `guest_meal.approve` | Reject (reason required) |
| GET | `/api/deposits/` | `deposit.view_own` / `deposit.approve` | List deposits |
| POST | `/api/deposits/` | `deposit.submit` | Submit deposit (OPEN month only) |
| POST | `/api/deposits/{id}/approve/` | `deposit.approve` | Approve |
| POST | `/api/deposits/{id}/reject/` | `deposit.approve` | Reject (reason required) |
| GET | `/api/expenses/` | `expense.create` | List expenses |
| POST | `/api/expenses/` | `expense.create` | Record expense (server assigns month) |
| PATCH | `/api/expenses/{id}/` | `expense.update` | Update expense |
| DELETE | `/api/expenses/{id}/` | `expense.delete` | Soft delete (reason required) |
| GET | `/api/adjustments/` | `adjustment.create` | List adjustments |
| POST | `/api/adjustments/` | `adjustment.create` | Post a manual correction (Admin only) |
| GET/PATCH | `/api/settings/` | `settings.manage` | System settings singleton |
| GET | `/api/audit-logs/` | `audit.view` | Read-only audit history |
| GET | `/api/dashboard/` | authenticated | Capability-shaped composite view |
| GET | `/api/reports/monthly/` | `report.view_own` / `report.view_all` | Monthly totals |
| GET | `/api/reports/members/` | `report.view_own` / `report.view_all` | Member-wise breakdown |
| GET | `/api/reports/balances/` | `report.view_own` / `report.view_all` | Balance history |

### Auth

#### `POST /api/auth/login/`

**Request body**

| Field | Type | Required |
|---|---|---|
| username | string | yes |
| password | string | yes |

**Success response — 200 OK**
```json
{
  "access": "eyJhbGciOi...",
  "refresh": "eyJhbGciOi...",
  "user": {
    "id": 4,
    "username": "admin",
    "email": "admin@example.com",
    "role": "ADMIN",
    "must_change_password": false
  }
}
```

**Error responses**

| Status | Code | Condition |
|---|---|---|
| 401 | — | Invalid credentials |

#### `GET /api/auth/me/`

**Success response — 200 OK**
```json
{
  "id": 4,
  "username": "admin",
  "email": "admin@example.com",
  "role": "ADMIN",
  "capabilities": ["month.create", "user.create", "adjustment.create", "..."]
}
```

### Users

#### `POST /api/users/`

**Capability:** `user.create`

**Request body**

| Field | Type | Required | Notes |
|---|---|---|---|
| username | string | yes | Immutable after creation |
| email | string | yes | |
| role | string | yes | `ADMIN` or `MEMBER` |
| phone | string | no | |
| first_name | string | no | |
| last_name | string | no | |

**Success response — 201 Created**
```json
{
  "id": 7,
  "username": "rafiq",
  "email": "rafiq@example.com",
  "role": "MEMBER",
  "is_active": true,
  "must_change_password": true,
  "temporary_password": "aB3$kL9!pQz2"
}
```
`temporary_password` appears **only in this response, once** — it is never
returned by any other endpoint.

**Error responses**

| Status | Code | Condition |
|---|---|---|
| 400 | — | Duplicate username/email |

#### `POST /api/users/{id}/deactivate/`

**Capability:** `user.deactivate`

**Error responses**

| Status | Code | Condition |
|---|---|---|
| 400 | `cannot_deactivate_active_manager` | Target holds the active ManagerAssignment for the open month |

### Months

#### `POST /api/months/`

**Capability:** `month.create`

**Request body**

| Field | Type | Required |
|---|---|---|
| name | string | yes |
| start_date | date | yes |
| end_date | date | yes |

**Success response — 201 Created**
```json
{
  "id": 3,
  "name": "October 2026",
  "start_date": "2026-10-01",
  "end_date": "2026-10-31",
  "status": "PLANNED"
}
```

#### `POST /api/months/{id}/open/`

**Capability:** `month.open`

**Success response — 200 OK** — status becomes `OPEN`; one `MonthMember`
row is created per active Member, with `opening_balance` carried from the
most recently closed month (0 if none).

#### `POST /api/months/{id}/close/`

**Capability:** `month.close`

**Success response — 200 OK** — status becomes `CLOSED`; `final_meal_rate`,
`final_total_expense`, and `rounding_residual` are set; every `MonthMember`
row is frozen with `finalized_at` set.

**Error responses**

| Status | Code | Condition |
|---|---|---|
| 400 | `month_close_blocked` | One or more validations failed — see `failures` array in the response body (pending deposits/guest meals, zero countable meal units, zero expenses, no active manager, etc.) |

#### `PUT /api/months/{id}/manager/`

**Capability:** `manager.assign`

**Request body**

| Field | Type | Required |
|---|---|---|
| user_id | integer | yes |

**Error responses**

| Status | Code | Condition |
|---|---|---|
| 400 | — | Target user is inactive, not a Member, or already the current manager |

### Meals

#### `POST /api/meals/`

**Capability:** `meal.submit`

**Request body**

| Field | Type | Required | Notes |
|---|---|---|---|
| meal_date | date | yes | ISO format |
| lunch | boolean | no | default false |
| dinner | boolean | no | default false |

**Success response — 201 Created**
```json
{
  "id": 55,
  "member": 7,
  "month": 3,
  "meal_date": "2026-10-02",
  "lunch": true,
  "dinner": false
}
```

**Error responses**

| Status | Code | Condition |
|---|---|---|
| 400 | `no_month_for_date` | meal_date falls outside any PLANNED/OPEN month |
| 403 | `deadline_passed` | Submitted after the cutoff for that date |

### Guest meals

#### `POST /api/guest-meals/`

**Capability:** `guest_meal.submit`

**Request body**

| Field | Type | Required | Notes |
|---|---|---|---|
| meal_date | date | yes | |
| lunch_quantity | integer | no | at least one quantity must be > 0 |
| dinner_quantity | integer | no | |
| remarks | string | no | |

**Success response — 201 Created**
```json
{
  "id": 12,
  "member": 7,
  "month": 3,
  "meal_date": "2026-10-05",
  "lunch_quantity": 2,
  "dinner_quantity": 0,
  "status": "PENDING"
}
```

**Error responses**

| Status | Code | Condition |
|---|---|---|
| 400 | `already_approved` | An approved request already exists for this member+date |

#### `POST /api/guest-meals/{id}/reject/`

**Capability:** `guest_meal.approve`

**Request body**

| Field | Type | Required |
|---|---|---|
| reason | string | yes |

### Deposits

#### `POST /api/deposits/`

**Capability:** `deposit.submit`

**Request body**

| Field | Type | Required | Notes |
|---|---|---|---|
| amount | decimal | yes | > 0 |
| payment_method | string | yes | `CASH`, `BKASH`, `NAGAD`, `BANK` |
| transaction_reference | string | required if not CASH | |
| payment_date | date | yes | |

**Error responses**

| Status | Code | Condition |
|---|---|---|
| 400 | `month_not_open` | No month is currently OPEN |

### Expenses

*(Confirmed directly from `serializers.py` during testing.)*

#### `POST /api/expenses/`

**Capability:** `expense.create`

**Request body**

| Field | Type | Required | Notes |
|---|---|---|---|
| category | string | yes | Grocery / Gas / Electricity / Water / Internet / Cleaning / Maintenance / Others |
| amount | decimal | yes | > 0 |
| expense_date | date | yes | Must fall within the open month |
| description | string | yes | |

`month` and `created_by` are **read-only** — the server assigns the current
`OPEN` month and the authenticated user automatically; do not send these
fields from the client.

**Success response — 201 Created**
```json
{
  "id": 21,
  "month": 3,
  "created_by": 5,
  "category": "Grocery",
  "amount": "1250.00",
  "expense_date": "2026-10-03",
  "description": "Weekly grocery run",
  "is_deleted": false,
  "deleted_at": null,
  "deleted_by": null,
  "delete_reason": null
}
```

**Error responses**

| Status | Code | Condition |
|---|---|---|
| 400 | `no_open_month` | No month is currently OPEN |

#### `DELETE /api/expenses/{id}/`

**Capability:** `expense.delete`

**Request body**

| Field | Type | Required |
|---|---|---|
| reason | string | yes |

Soft delete only — sets `is_deleted`, `deleted_at`, `deleted_by`,
`delete_reason`. The record is never physically removed.

### Adjustments

#### `POST /api/adjustments/`

**Capability:** `adjustment.create` (Admin only)

**Request body**

| Field | Type | Required | Notes |
|---|---|---|---|
| month | integer | yes | Must be OPEN |
| member | integer | yes | |
| direction | string | yes | `DEBIT` or `CREDIT` |
| amount | decimal | yes | > 0 |
| reason | string | yes | |
| source_entity_type | string | no | |
| source_entity_id | integer | no | |

**⚠️ Known gap:** this endpoint was not exercised by the automated
end-to-end workflow test (only the system-generated rounding-residual
adjustment path was). Manually verify a real `POST` here before relying on
it.

### Reports

#### `GET /api/reports/monthly/?month_id=`

**Success response — 200 OK**
```json
{
  "month_id": 3,
  "rate_status": "ESTIMATED",
  "total_expense": "5400.00",
  "countable_meal_units": 210,
  "meal_rate": "25.7143"
}
```

`rate_status` is always explicitly `"ESTIMATED"` or `"FINAL"` — never
inferred silently from month status alone.

### Known gaps

- `Adjustment` creation endpoint untested end-to-end (see above).
- Settings retrieve/update endpoint shape not confirmed against actual
  serializer — verify field names match `SystemSetting` model exactly.
- Reopen endpoint (`POST /api/months/{id}/reopen/`) was part of the
  original Rev 2 design but was **dropped** in the Rev 3 rebuild per
  project scope — confirm no dangling reference to it remains in
  `urls.py`.

---

## Deployment

Backend and frontend are deployed as two separate services:

- **Backend:** gunicorn + whitenoise, hosted on Render/Railway/Fly.io. Set
  `DEBUG=False`, `ALLOWED_HOSTS`, and `DATABASE_URL` via environment
  variables in the host's dashboard.
- **Frontend:** static React build, hosted on Vercel/Netlify, pointing at
  the deployed backend URL via an environment variable.
- **CORS:** `django-cors-headers`, with `CORS_ALLOWED_ORIGINS` set to the
  frontend's deployed domain.

If deploying on SQLite rather than switching to Postgres in production,
confirm your host provides a **persistent volume/disk** — most PaaS hosts
use an ephemeral filesystem that wipes a local SQLite file on every
redeploy.

---

## Testing

Tests live under `apps/<app_name>/tests/`. Run the full suite:

```bash
python manage.py test apps
```

The most important single test in the project is the full monthly-cycle
workflow test, which exercises every major endpoint end-to-end through
real HTTP calls via DRF's `APIClient` rather than testing components in
isolation:

```bash
python manage.py test apps.months.tests.test_full_workflow -v 2
```

This test covers: admin bootstrap, member creation, month open with
roster/carry-forward, manager assignment, meal + guest-meal submission and
approval, deposit submission and approval, expense recording, dashboard
access by role, month close with reconciliation, and balance carry-forward
into a second month. Any change to core business logic should be verified
against this test before being considered done.

---

## License

MIT — see `LICENSE`.

*(Confirm this is the intended license; update this section and add the
LICENSE file if a different license applies.)*

---

## Author

Built by Nahiduzzaman as a portfolio project.