from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from zoneinfo import ZoneInfo

from django.db.models import Q
from django.utils import timezone

from apps.expenses.models import Expense
from apps.guest_meals.models import GuestMeal
from apps.meals.models import Meal
from apps.months.models import Month
from apps.settings_app.models import SystemSetting


class NoMonthForDateError(ValueError):
    """Raised when no planned/open month covers a date."""


def resolve_month_for_date(meal_date):
    month = (
        Month.objects.filter(start_date__lte=meal_date, end_date__gte=meal_date)
        .filter(Q(status=Month.Status.PLANNED) | Q(status=Month.Status.OPEN))
        .order_by('start_date')
        .first()
    )
    if month is None:
        raise NoMonthForDateError(f'No PLANNED or OPEN month covers {meal_date.isoformat()}')
    return month


def is_meal_submission_deadline_passed(meal_date):
    setting = SystemSetting.objects.filter(pk=1).first()
    if setting is None or setting.meal_submission_deadline is None:
        return False

    try:
        zone = ZoneInfo(setting.timezone)
    except Exception:
        zone = ZoneInfo('UTC')

    local_now = timezone.now().astimezone(zone)
    deadline_date = meal_date - timedelta(days=1)
    if local_now.date() != deadline_date:
        return False

    deadline_dt = datetime.combine(deadline_date, setting.meal_submission_deadline).replace(tzinfo=zone)
    return local_now > deadline_dt


def estimate_open_month_rate(month):
    if month is None or month.status == Month.Status.CLOSED:
        return month.final_meal_rate if month and month.final_meal_rate is not None else Decimal('0')

    member_meal_units = sum((1 if m.lunch else 0) + (1 if m.dinner else 0) for m in Meal.objects.filter(month=month))
    guest_units = sum(g.lunch_quantity + g.dinner_quantity for g in GuestMeal.objects.filter(month=month, status=GuestMeal.Status.APPROVED))
    countable_units = member_meal_units + guest_units
    total_expense = sum(e.amount for e in Expense.objects.filter(month=month, is_deleted=False))

    if countable_units == 0:
        return Decimal('0')

    return (Decimal(total_expense) / Decimal(countable_units)).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
