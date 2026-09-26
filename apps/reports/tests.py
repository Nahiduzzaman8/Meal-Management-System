from decimal import Decimal

from django.test import TestCase
from django.contrib.auth import get_user_model

from apps.deposits.models import Deposit
from apps.expenses.models import Expense
from apps.guest_meals.models import GuestMeal
from apps.meals.models import Meal
from apps.months.models import ManagerAssignment, Month, MonthMember

User = get_user_model()


class DashboardAndReportsTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='AdminPass!234',
            role='ADMIN',
            must_change_password=False,
        )
        self.member = User.objects.create_user(
            username='member',
            email='member@example.com',
            password='MemberPass!234',
            role='MEMBER',
            must_change_password=False,
        )
        self.month = Month.objects.create(
            name='2026-09',
            start_date='2026-09-01',
            end_date='2026-09-30',
            status=Month.Status.OPEN,
            created_by=self.admin,
        )
        MonthMember.objects.create(month=self.month, member=self.member, joined_on='2026-09-01', opening_balance=Decimal('200.00'))
        ManagerAssignment.objects.create(month=self.month, user=self.member, assigned_by=self.admin)
        Meal.objects.create(member=self.member, month=self.month, meal_date='2026-09-02', lunch=True, dinner=False)
        Meal.objects.create(member=self.member, month=self.month, meal_date='2026-09-03', lunch=False, dinner=True)
        GuestMeal.objects.create(
            member=self.member,
            month=self.month,
            meal_date='2026-09-04',
            lunch_quantity=1,
            dinner_quantity=0,
            status=GuestMeal.Status.APPROVED,
        )
        Expense.objects.create(
            month=self.month,
            created_by=self.admin,
            category='Grocery',
            amount=Decimal('180.00'),
            expense_date='2026-09-05',
            description='Groceries',
        )
        Deposit.objects.create(
            member=self.member,
            month=self.month,
            amount=Decimal('50.00'),
            payment_method=Deposit.PaymentMethod.CASH,
            payment_date='2026-09-06',
            status=Deposit.Status.PENDING,
        )

    def _token(self, user):
        response = self.client.post(
            '/api/auth/login/',
            {'username': user.username, 'password': 'AdminPass!234' if user.username == 'admin' else 'MemberPass!234'},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()['access']

    def test_dashboard_payload_and_role_access(self):
        token = self._token(self.member)
        response = self.client.get('/api/dashboard/', HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body['current_month']['id'], self.month.id)
        self.assertEqual(body['meal_units'], 2)
        self.assertEqual(body['guest_meal_units'], 1)
        self.assertIn('estimated_meal_rate', body)
        self.assertEqual(body['pending_deposit_count'], 1)
        self.assertEqual(body['pending_guest_meal_count'], 0)
        self.assertEqual(body['total_expense_so_far'], 180.0)

        admin_token = self._token(self.admin)
        admin_response = self.client.get('/api/dashboard/', HTTP_AUTHORIZATION=f'Bearer {admin_token}')
        self.assertEqual(admin_response.status_code, 200)
        admin_body = admin_response.json()
        self.assertEqual(admin_body['total_active_members'], 1)
        self.assertIsNotNone(admin_body['current_manager'])

    def test_monthly_report_rates_and_member_access(self):
        token = self._token(self.member)
        response = self.client.get(f'/api/reports/monthly/?month_id={self.month.id}', HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body['rate_status'], 'ESTIMATED')
        self.assertIn('estimated_meal_rate', body)
        self.assertIn('members', body)

        admin_token = self._token(self.admin)
        admin_response = self.client.get(f'/api/reports/members/?month_id={self.month.id}', HTTP_AUTHORIZATION=f'Bearer {admin_token}')
        self.assertEqual(admin_response.status_code, 200)
        self.assertGreater(len(admin_response.json()), 0)

    def test_balances_report_restricts_other_members(self):
        other = User.objects.create_user(username='other', email='other@example.com', password='OtherPass!234', role='MEMBER', must_change_password=False)
        ManagerAssignment.objects.filter(month=self.month, user=self.member).delete()
        token = self._token(self.member)

        response = self.client.get(f'/api/reports/balances/?member_id={other.id}', HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(response.status_code, 403)

        self_response = self.client.get(f'/api/reports/balances/?member_id={self.member.id}', HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(self_response.status_code, 200)
