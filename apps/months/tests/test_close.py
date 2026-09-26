from django.test import TestCase
from django.contrib.auth import get_user_model
from decimal import Decimal
from django.utils import timezone

from apps.months.models import Month, MonthMember
from apps.meals.models import Meal
from apps.guest_meals.models import GuestMeal
from apps.expenses.models import Expense
from apps.deposits.models import Deposit
from apps.adjustments.models import Adjustment

User = get_user_model()


class ReconciliationTest(TestCase):
    def setUp(self):
        # create 13 members
        self.admin = User.objects.create(username='admin', role='ADMIN', is_superuser=True)
        self.members = [User.objects.create(username=f'm{i}', role='MEMBER') for i in range(13)]
        # create a planned month then open it
        self.month = Month.objects.create(name='2026-09', start_date='2026-09-01', end_date='2026-09-30', status=Month.Status.OPEN, created_by=self.admin)
        # create MonthMember rows manually with varied opening balances
        today = timezone.now().date()
        for i, m in enumerate(self.members):
            opening = Decimal('10.00') if i == 0 else Decimal('0')
            mm = MonthMember.objects.create(month=self.month, member=m, joined_on=today, opening_balance=opening)
        # create meals: distributed unevenly
        # first member has many meals
        for i, m in enumerate(self.members):
            # give each member i+1 meals
            for day in range(i+1):
                Meal.objects.create(member=m, month=self.month, meal_date=f'2026-09-{(day%28)+1}', lunch=True if day%2==0 else False, dinner=True if day%2==1 else False)
        # add guest meals for some
        GuestMeal.objects.create(member=self.members[0], month=self.month, meal_date='2026-09-05', lunch_quantity=1, dinner_quantity=0, status=GuestMeal.Status.APPROVED)
        # create expenses: total doesn't divide evenly by meal units
        Expense.objects.create(month=self.month, created_by=self.admin, category='Grocery', amount=Decimal('1234.56'), expense_date='2026-09-15', description='Groceries')
        # create some deposits and adjustments
        Deposit.objects.create(member=self.members[0], month=self.month, amount=Decimal('50.00'), payment_method=Deposit.PaymentMethod.CASH, payment_date='2026-09-10', status=Deposit.Status.APPROVED)
        Adjustment.objects.create(month=self.month, member=self.members[1], direction=Adjustment.Direction.CREDIT, amount=Decimal('5.00'), reason='Test adj', created_by=self.admin)
        # assign a manager for the month
        from apps.months.models import ManagerAssignment
        ManagerAssignment.objects.create(month=self.month, user=self.admin, assigned_by=self.admin)

    def test_reconciliation_and_carry_forward(self):
        # call close logic
        from apps.months.services import close_month
        result = close_month(self.month.id, acting_user=self.admin)
        self.assertNotIn('code', result)
        # reload members
        mms = list(MonthMember.objects.filter(month=self.month))
        total_costs = sum(mm.total_cost for mm in mms)
        total_expense = Decimal('1234.56')
        # after residual applied the member total_costs must reconcile exactly
        self.assertEqual(total_costs, total_expense)
        # open a new month and verify opening balances carried
        from apps.months.services import open_month
        new_month = Month.objects.create(name='2026-10', start_date='2026-10-01', end_date='2026-10-31', status=Month.Status.PLANNED, created_by=self.admin)
        open_month(new_month.id, acting_user=self.admin)
        new_mms = MonthMember.objects.filter(month=new_month)
        # check that opening balances equal previous closing balances
        old = {mm.member.username: mm.closing_balance for mm in mms}
        for nm in new_mms:
            self.assertEqual(nm.opening_balance, old[nm.member.username])
