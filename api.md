# Meal Management System API

Base URL prefix: `/api/`

Authentication:

- Most endpoints require JWT authentication via `Authorization: Bearer <access_token>`.
- `auth/login`, `auth/refresh`, and `auth/logout` are available for token handling.

---

## Authentication and Users

### Auth

- `POST /api/auth/login/`
  - Login and receive JWT tokens.
  - Response includes `access`, `refresh`, and `user` profile payload.

- `POST /api/auth/refresh/`
  - Refresh an access token using a valid refresh token.

- `POST /api/auth/logout/`
  - Blacklist a refresh token.
  - Body expects `refresh`.

- `GET /api/auth/me/`
  - Fetch the authenticated user's profile and effective capabilities.

- `POST /api/auth/password/change/`
  - Change the currently authenticated user's password.

### Users

- `GET /api/users/`
  - List users.
  - Supports query filters: `role`, `is_active`, `search`.

- `POST /api/users/`
  - Create a new user.

- `GET /api/users/<id>/`
  - Fetch a single user record.

- `PATCH /api/users/<id>/`
  - Update a user record.

- `POST /api/users/<id>/deactivate/`
  - Deactivate a user.
  - Blocks deactivation if the user is the active manager for the open month.

- `POST /api/users/<id>/reactivate/`
  - Reactivate a user.

- `POST /api/users/<id>/reset-password/`
  - Reset a user's password and force password change on next login.

---

## Months

- `POST /api/months/`
  - Create a month.
  - Requires month name, start date, and end date.

- `POST /api/months/<id>/open/`
  - Open a planned month.
  - Creates MonthMember rows for active members and validates no other open month exists.

- `POST /api/months/<id>/close/`
  - Attempt to close an open month.
  - Validates pending deposits, guest meals, meal units, expense presence, active members, and active manager before finalizing.

- `GET /api/months/<id>/members/`
  - Get member rows for a month.

- `PUT /api/months/<id>/manager/`
  - Assign or update the manager for a month.

---

## Meals

- `GET /api/meals/`
  - Get meals for the authenticated user by default.
  - If the caller has manager-level access and passes `?month=<id>`, it can fetch all meals for that month.

- `POST /api/meals/`
  - Submit or upsert a member meal for a date.
  - Validates that the date falls inside a `PLANNED` or `OPEN` month and that the deadline has not passed.

---

## Guest Meals

- `GET /api/guest-meals/`
  - Get guest meal submissions for the authenticated user by default.
  - If the caller has approval access and passes `?month=<id>`, it can fetch all guest meals for that month.

- `POST /api/guest-meals/`
  - Submit a guest meal for a date.
  - Accepts lunch and dinner quantities.
  - Requires a valid planned/open month and a still-open submission deadline.

- `POST /api/guest-meals/<id>/approve/`
  - Approve a pending guest meal.
  - Requires `guest_meal.approve` capability.

- `POST /api/guest-meals/<id>/reject/`
  - Reject a pending guest meal.
  - Requires a `reason` in the request body.

---

## Deposits

- `GET /api/deposits/`
  - Get deposits for the authenticated user by default.
  - If the caller has approval access and passes `?month=<id>`, it can fetch all deposits for that month.

- `POST /api/deposits/`
  - Submit a deposit.
  - Accepts amount, payment method, payment date, and optional transaction reference.

- `POST /api/deposits/<id>/approve/`
  - Approve a pending deposit.

- `POST /api/deposits/<id>/reject/`
  - Reject a pending deposit.
  - Requires a `reason`.

---

## Expenses

- `GET /api/expenses/`
  - List non-deleted expenses.
  - Supports filtering by `?month=<id>`.

- `POST /api/expenses/`
  - Create an expense.

- `PATCH /api/expenses/<id>/`
  - Update an expense.

- `DELETE /api/expenses/<id>/delete/`
  - Soft-delete an expense.
  - Requires a deletion `reason`.

---

## Adjustments

- `GET /api/adjustments/`
  - List adjustment records.

- `POST /api/adjustments/`
  - Create an adjustment.

---

## Dashboard

- `GET /api/dashboard/`
  - Return the current open/planned month summary plus user-specific totals.
  - Includes meal units, guest meal units, estimated meal rate, pending deposits, pending guest meals, total expense so far, and current manager info when relevant.

---

## Reports

- `GET /api/reports/monthly/?month_id=<id>`
  - Monthly report for a month.
  - Returns month status, rate info, and per-member summary rows.

- `GET /api/reports/members/?month_id=<id>`
  - Member report for a month.
  - Returns member-level monthly statistics.

- `GET /api/reports/balances/?member_id=<id>`
  - Finalized balance history for a specific member.
  - Restricts access to the member themselves or users with `report.view_all` capability.

---

## Capability Notes

The app uses role-based capabilities plus active-manager capabilities for the currently open month.

Core roles:

- `ADMIN`
- `MEMBER`

Manager capabilities are granted through active `ManagerAssignment` records rather than a separate `MANAGER` user role.
