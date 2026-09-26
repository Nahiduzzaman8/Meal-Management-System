from decimal import Decimal

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.deposits.models import Deposit
from apps.expenses.models import Expense
from apps.guest_meals.models import GuestMeal
from apps.meals.models import Meal
from apps.months.models import ManagerAssignment, Month, MonthMember
from apps.months.utils import estimate_open_month_rate


class DashboardView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        month = Month.objects.filter(status__in=[Month.Status.PLANNED, Month.Status.OPEN]).order_by('-start_date').first()
        payload = {
            'current_month': None,
            'meal_units': 0,
            'guest_meal_units': 0,
            'closing_balance': Decimal('0'),
        }

        if month is not None:
            payload['current_month'] = {
                'id': month.id,
                'name': month.name,
                'status': month.status,
            }
            meal_units = sum((1 if m.lunch else 0) + (1 if m.dinner else 0) for m in Meal.objects.filter(member=request.user, month=month))
            guest_units = sum(g.lunch_quantity + g.dinner_quantity for g in GuestMeal.objects.filter(member=request.user, month=month, status=GuestMeal.Status.APPROVED))
            payload['meal_units'] = meal_units
            payload['guest_meal_units'] = guest_units

            member_row = MonthMember.objects.filter(member=request.user, month=month).first()
            if member_row and member_row.finalized_at is not None:
                payload['closing_balance'] = member_row.closing_balance or Decimal('0')
            else:
                estimated_rate = estimate_open_month_rate(month)
                if estimated_rate is not None:
                    live_total = Decimal(meal_units + guest_units) * estimated_rate
                    payload['closing_balance'] = Decimal((member_row.closing_balance or Decimal('0')) if member_row else Decimal('0')) + live_total if member_row else live_total
                else:
                    payload['closing_balance'] = Decimal('0')

        if request.user.has_capability('meal.view_all') or request.user.has_capability('deposit.approve') or request.user.has_capability('guest_meal.approve'):
            if month is not None:
                payload['pending_deposit_count'] = Deposit.objects.filter(month=month, status=Deposit.Status.PENDING).count()
                payload['pending_guest_meal_count'] = GuestMeal.objects.filter(month=month, status=GuestMeal.Status.PENDING).count()
                payload['total_expense_so_far'] = sum(e.amount for e in Expense.objects.filter(month=month, is_deleted=False))
                payload['estimated_meal_rate'] = estimate_open_month_rate(month)

        if request.user.is_superuser or request.user.role == 'ADMIN':
            if month is not None:
                payload['total_active_members'] = MonthMember.objects.filter(month=month, left_on__isnull=True).count()
                payload['current_manager'] = None
                current_manager = ManagerAssignment.current_manager(month)
                if current_manager:
                    payload['current_manager'] = {
                        'id': current_manager.id,
                        'username': current_manager.username,
                    }

        return Response(payload)
