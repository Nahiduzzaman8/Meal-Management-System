from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.months.models import Month, MonthMember

User = get_user_model()


class FullMonthlyWorkflowApiTest(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(
            username='admin_workflow',
            email='admin_workflow@example.com',
            password='AdminPass!234',
            role='ADMIN',
            must_change_password=False,
        )
        self.admin_client = APIClient()
        self.member_clients = {}
        self.members = []

    def login_via_api(self, client, username, password, step_label):
        response = client.post(
            '/api/auth/login/',
            {'username': username, 'password': password},
            format='json',
        )
        self.assertEqual(
            response.status_code,
            200,
            f"{step_label} failed: login for {username} returned {response.status_code} with {response.content}",
        )
        payload = response.json()
        self.assertIn('access', payload, f"{step_label} failed: login payload missing access token for {username}")
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {payload['access']}")
        return payload['access']

    def change_password_via_api(self, client, current_password, new_password, step_label):
        response = client.post(
            '/api/auth/password/change/',
            {'current_password': current_password, 'new_password': new_password},
            format='json',
        )
        self.assertEqual(
            response.status_code,
            200,
            f"{step_label} failed: password change returned {response.status_code} with {response.content}",
        )
        return response

    def create_member_via_api(self, username, email):
        response = self.admin_client.post(
            '/api/users/',
            {
                'username': username,
                'email': email,
                'role': 'MEMBER',
                'first_name': username,
                'last_name': 'Member',
                'phone': '123456789',
            },
            format='json',
        )
        self.assertEqual(
            response.status_code,
            201,
            f"Step 2 failed: creating member {username} returned {response.status_code} with {response.content}",
        )
        payload = response.json()
        temporary_password = payload.get('temporary_password')
        self.assertIsNotNone(
            temporary_password,
            f"Step 2 failed: member {username} creation payload missing temporary_password",
        )
        return payload, temporary_password

    def test_full_monthly_workflow_end_to_end(self):
        # Step 1: Admin login
        self.login_via_api(self.admin_client, 'admin_workflow', 'AdminPass!234', 'Step 1')

        # Step 2: Create 3 members via API and capture temporary_passwords
        member_specs = [
            ('member_1', 'member1@example.com'),
            ('member_2', 'member2@example.com'),
            ('member_3', 'member3@example.com'),
        ]
        temp_passwords = {}
        for username, email in member_specs:
            payload, temp_password = self.create_member_via_api(username, email)
            self.members.append({'username': username, 'email': email, 'id': payload['id'], 'temp_password': temp_password})
            temp_passwords[username] = temp_password

        # Step 3: Log in as each member and clear must_change_password
        for member in self.members:
            client = APIClient()
            self.login_via_api(client, member['username'], member['temp_password'], f"Step 3 ({member['username']})")
            self.change_password_via_api(client, member['temp_password'], f"{member['username']}NewPass!123", f"Step 3 ({member['username']})")
            self.member_clients[member['username']] = client
            member['password'] = f"{member['username']}NewPass!123"

        # Step 4: Admin creates and opens month; assert 3 MonthMember rows with zero opening_balance
        month_response = self.admin_client.post(
            '/api/months/',
            {'name': '2026-09', 'start_date': '2026-09-01', 'end_date': '2026-09-30'},
            format='json',
        )
        self.assertEqual(
            month_response.status_code,
            201,
            f"Step 4 failed: month create returned {month_response.status_code} with {month_response.content}",
        )
        month_id = month_response.json()['id']

        open_month_response = self.admin_client.post(f'/api/months/{month_id}/open/', {}, format='json')
        self.assertEqual(
            open_month_response.status_code,
            200,
            f"Step 4 failed: month open returned {open_month_response.status_code} with {open_month_response.content}",
        )
        member_rows = list(MonthMember.objects.filter(month_id=month_id).order_by('member_id'))
        self.assertEqual(
            len(member_rows),
            3,
            f"Step 4 failed: expected 3 MonthMember rows after open, got {len(member_rows)}",
        )
        for row in member_rows:
            self.assertEqual(
                row.opening_balance,
                Decimal('0'),
                f"Step 4 failed: month member opening_balance for {row.member_id} was {row.opening_balance}, expected 0",
            )

        # Step 5: Admin assigns manager; member 1 proves manager-grantable caps on /api/auth/me/
        member_1 = self.members[0]
        assign_response = self.admin_client.put(
            f'/api/months/{month_id}/manager/',
            {'user_id': member_1['id']},
            format='json',
        )
        self.assertEqual(
            assign_response.status_code,
            200,
            f"Step 5 failed: manager assignment returned {assign_response.status_code} with {assign_response.content}",
        )

        manager_client = self.member_clients[member_1['username']]
        me_response = manager_client.get('/api/auth/me/')
        self.assertEqual(
            me_response.status_code,
            200,
            f"Step 5 failed: auth/me for manager returned {me_response.status_code} with {me_response.content}",
        )
        capabilities = set(me_response.json().get('capabilities', []))
        self.assertIn('expense.create', capabilities, f"Step 5 failed: manager did not receive manager-grantable capability; capabilities={sorted(capabilities)}")
        self.assertIn('guest_meal.approve', capabilities, f"Step 5 failed: manager missing guest_meal.approve capability; capabilities={sorted(capabilities)}")

        # Step 6: Each member submits meals for 3 dates with different lunch/dinner combos
        date_sets = [
            ('2026-09-04', True, False),
            ('2026-09-05', False, True),
            ('2026-09-06', True, True),
        ]
        for member in self.members:
            client = self.member_clients[member['username']]
            for meal_date, lunch, dinner in date_sets:
                meal_response = client.post(
                    '/api/meals/',
                    {'meal_date': meal_date, 'lunch': lunch, 'dinner': dinner},
                    format='json',
                )
                self.assertEqual(
                    meal_response.status_code,
                    201,
                    f"Step 6 failed for {member['username']} on {meal_date}: {meal_response.status_code} {meal_response.content}",
                )

        # Step 7: Guest meal submission and approval
        member_2 = self.members[1]
        member_2_client = self.member_clients[member_2['username']]
        guest_post = member_2_client.post(
            '/api/guest-meals/',
            {'meal_date': '2026-09-07', 'lunch_quantity': 1, 'dinner_quantity': 0, 'remarks': 'guest meal'},
            format='json',
        )
        self.assertEqual(
            guest_post.status_code,
            201,
            f"Step 7 failed: member 2 guest meal create returned {guest_post.status_code} with {guest_post.content}",
        )
        guest_id = guest_post.json()['id']
        guest_approve = manager_client.post(f'/api/guest-meals/{guest_id}/approve/', {}, format='json')
        self.assertEqual(
            guest_approve.status_code,
            200,
            f"Step 7 failed: guest meal approval returned {guest_approve.status_code} with {guest_approve.content}",
        )
        self.assertEqual(
            guest_approve.json()['status'],
            'APPROVED',
            f"Step 7 failed: guest meal status after approval should be APPROVED but was {guest_approve.json().get('status')}",
        )

        # Step 8: Deposit submission and approval
        member_3 = self.members[2]
        member_3_client = self.member_clients[member_3['username']]
        deposit_post = member_3_client.post(
            '/api/deposits/',
            {'amount': '75.00', 'payment_method': 'CASH', 'transaction_reference': '', 'payment_date': '2026-09-08'},
            format='json',
        )
        self.assertEqual(
            deposit_post.status_code,
            201,
            f"Step 8 failed: member 3 deposit create returned {deposit_post.status_code} with {deposit_post.content}",
        )
        deposit_id = deposit_post.json()['id']
        deposit_approve = manager_client.post(f'/api/deposits/{deposit_id}/approve/', {}, format='json')
        self.assertEqual(
            deposit_approve.status_code,
            200,
            f"Step 8 failed: deposit approval returned {deposit_approve.status_code} with {deposit_approve.content}",
        )
        self.assertEqual(
            deposit_approve.json()['status'],
            'APPROVED',
            f"Step 8 failed: deposit status after approval should be APPROVED but was {deposit_approve.json().get('status')}",
        )

        # Step 9: Manager creates two expenses
        expense_1 = manager_client.post(
            '/api/expenses/',
            {'month': month_id, 'category': 'Grocery', 'amount': '150.50', 'expense_date': '2026-09-11', 'description': 'Groceries'},
            format='json',
        )
        self.assertEqual(
            expense_1.status_code,
            201,
            f"Step 9 failed: first expense create returned {expense_1.status_code} with {expense_1.content}",
        )

        expense_2 = manager_client.post(
            '/api/expenses/',
            {'month': month_id, 'category': 'Gas', 'amount': '200.75', 'expense_date': '2026-09-20', 'description': 'Fuel'},
            format='json',
        )
        self.assertEqual(
            expense_2.status_code,
            201,
            f"Step 9 failed: second expense create returned {expense_2.status_code} with {expense_2.content}",
        )
        total_expense = Decimal('150.50') + Decimal('200.75')

        # Step 10: Dashboard should differ for member vs manager
        member_dashboard = member_3_client.get('/api/dashboard/')
        self.assertEqual(
            member_dashboard.status_code,
            200,
            f"Step 10 failed: member dashboard returned {member_dashboard.status_code} with {member_dashboard.content}",
        )
        member_payload = member_dashboard.json()
        self.assertNotIn('total_expense_so_far', member_payload, f"Step 10 failed: plain member should not see manager dashboard field. Payload={member_payload}")

        manager_dashboard = manager_client.get('/api/dashboard/')
        self.assertEqual(
            manager_dashboard.status_code,
            200,
            f"Step 10 failed: manager dashboard returned {manager_dashboard.status_code} with {manager_dashboard.content}",
        )
        manager_payload = manager_dashboard.json()
        self.assertIn('total_expense_so_far', manager_payload, f"Step 10 failed: manager dashboard missing total_expense_so_far. Payload={manager_payload}")
        self.assertIn('pending_deposit_count', manager_payload, f"Step 10 failed: manager dashboard missing pending_deposit_count. Payload={manager_payload}")

        # Step 11: Admin closes the month and asserts it succeeds
        close_response = self.admin_client.post(f'/api/months/{month_id}/close/', {}, format='json')
        self.assertEqual(
            close_response.status_code,
            200,
            f"Step 11 failed: close returned {close_response.status_code} with {close_response.content}",
        )
        close_payload = close_response.json()
        self.assertNotIn('code', close_payload, f"Step 11 failed: close returned blocked payload instead of success: {close_payload}")
        self.assertEqual(close_payload.get('status'), 'closed', f"Step 11 failed: close response status was {close_payload.get('status')}, payload={close_payload}")

        # Step 12: API monthly member rows should reconcile exactly against total expense entered in Step 9
        members_response = self.admin_client.get(f'/api/months/{month_id}/members/')
        self.assertEqual(
            members_response.status_code,
            200,
            f"Step 12 failed: members list returned {members_response.status_code} with {members_response.content}",
        )
        rows = members_response.json()
        self.assertTrue(rows, f"Step 12 failed: received no member rows after close")
        member_total_cost_sum = sum(Decimal(str(row['total_cost'])) for row in rows)
        self.assertEqual(
            member_total_cost_sum,
            total_expense,
            f"Step 12 failed: sum(total_cost)={member_total_cost_sum} does not equal total_expense={total_expense}; row_data={rows}",
        )
        closing_balances = {int(row['member']): Decimal(str(row['closing_balance'])) for row in rows}

        # Step 13: Create a second month and ensure opening balances match prior closing balances
        second_month_response = self.admin_client.post(
            '/api/months/',
            {'name': '2026-10', 'start_date': '2026-10-01', 'end_date': '2026-10-31'},
            format='json',
        )
        self.assertEqual(
            second_month_response.status_code,
            201,
            f"Step 13 failed: second month create returned {second_month_response.status_code} with {second_month_response.content}",
        )
        second_month_id = second_month_response.json()['id']

        second_open = self.admin_client.post(f'/api/months/{second_month_id}/open/', {}, format='json')
        self.assertEqual(
            second_open.status_code,
            200,
            f"Step 13 failed: second month open returned {second_open.status_code} with {second_open.content}",
        )
        second_members_response = self.admin_client.get(f'/api/months/{second_month_id}/members/')
        self.assertEqual(
            second_members_response.status_code,
            200,
            f"Step 13 failed: second month members list returned {second_members_response.status_code} with {second_members_response.content}",
        )
        second_rows = second_members_response.json()
        second_opening_balances = {int(row['member']): Decimal(str(row['opening_balance'])) for row in second_rows}
        for member_id, closing_balance in closing_balances.items():
            self.assertEqual(
                second_opening_balances.get(member_id),
                closing_balance,
                f"Step 13 failed: opening_balance for member {member_id} mismatch: new={second_opening_balances.get(member_id)}, old={closing_balance}",
            )

        # Step 14: Use the already-open second month and assert the close guard blocks a pending deposit.
        blocked_month_id = second_month_id

        pending_deposit = member_3_client.post(
            '/api/deposits/',
            {'amount': '11.00', 'payment_method': 'CASH', 'transaction_reference': '', 'payment_date': '2026-10-05'},
            format='json',
        )
        self.assertEqual(
            pending_deposit.status_code,
            201,
            f"Step 14 failed: pending deposit creation in open second month returned {pending_deposit.status_code} with {pending_deposit.content}",
        )

        blocked_close = self.admin_client.post(f'/api/months/{blocked_month_id}/close/', {}, format='json')
        self.assertEqual(
            blocked_close.status_code,
            400,
            f"Step 14 failed: close on second month with pending deposit should be blocked with 400, got {blocked_close.status_code} with {blocked_close.content}",
        )
        blocked_payload = blocked_close.json()
        self.assertIn('code', blocked_payload, f"Step 14 failed: blocked close payload missing 'code': {blocked_payload}")
        self.assertEqual(blocked_payload['code'], 'month_close_blocked', f"Step 14 failed: blocked close code was {blocked_payload.get('code')}, payload={blocked_payload}")
        self.assertTrue(
            blocked_payload.get('failures'),
            f"Step 14 failed: blocked close failures list should be non-empty; payload={blocked_payload}",
        )
        self.assertTrue(
            any('pending_deposits' in failure for failure in blocked_payload['failures']),
            f"Step 14 failed: pending deposit failure not present in {blocked_payload['failures']}",
        )
