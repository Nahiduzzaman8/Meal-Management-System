from decimal import Decimal, ROUND_HALF_UP, getcontext
from django.utils import timezone
from django.db import transaction

from apps.months.models import Month, MonthMember
from apps.meals.models import Meal
from apps.guest_meals.models import GuestMeal
from apps.expenses.models import Expense
from apps.adjustments.models import Adjustment
from apps.deposits.models import Deposit

getcontext().prec = 28


def finalize_month(month: Month, acting_user=None):
    """Finalize accounting for a month. Returns dict with summary values."""
    from decimal import Decimal


    # a. countable meal units (member meals: each lunch/dinner counts as 1 unit)
    member_meal_units = sum(((1 if m.lunch else 0) + (1 if m.dinner else 0)) for m in Meal.objects.filter(month=month))

    guest_qs = GuestMeal.objects.filter(month=month, status=GuestMeal.Status.APPROVED)
    guest_units = sum((g.lunch_quantity + g.dinner_quantity) for g in guest_qs)

    countable_meal_units = member_meal_units + guest_units

    # b. total_expense
    total_expense = sum(e.amount for e in Expense.all_objects.filter(month=month, is_deleted=False))

    if countable_meal_units == 0:
        final_meal_rate = Decimal('0')
    else:
        final_meal_rate = (Decimal(total_expense) / Decimal(countable_meal_units)).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)

    members = list(MonthMember.objects.filter(month=month))

    # d. per-member computations
    sum_member_costs = Decimal('0')
    for mm in members:
        # compute meal units
        meals = Meal.objects.filter(month=month, member=mm.member)
        lunch = sum(1 for m in meals if m.lunch)
        dinner = sum(1 for m in meals if m.dinner)
        mm.lunch_count = lunch
        mm.dinner_count = dinner
        mm.meal_units = lunch + dinner

        guest_rows = GuestMeal.objects.filter(month=month, member=mm.member, status=GuestMeal.Status.APPROVED)
        guest_lunch = sum(g.lunch_quantity for g in guest_rows)
        guest_dinner = sum(g.dinner_quantity for g in guest_rows)
        mm.guest_lunch_count = guest_lunch
        mm.guest_dinner_count = guest_dinner
        mm.guest_meal_units = guest_lunch + guest_dinner

        mm.meal_rate_applied = final_meal_rate
        mm.meal_cost = (Decimal(mm.meal_units) * final_meal_rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        mm.guest_meal_cost = (Decimal(mm.guest_meal_units) * final_meal_rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        debits = Adjustment.objects.filter(month=month, member=mm.member, direction=Adjustment.Direction.DEBIT).aggregate_total_amount() if hasattr(Adjustment.objects, 'aggregate_total_amount') else sum(a.amount for a in Adjustment.objects.filter(month=month, member=mm.member, direction=Adjustment.Direction.DEBIT))
        credits = Adjustment.objects.filter(month=month, member=mm.member, direction=Adjustment.Direction.CREDIT).aggregate_total_amount() if hasattr(Adjustment.objects, 'aggregate_total_amount') else sum(a.amount for a in Adjustment.objects.filter(month=month, member=mm.member, direction=Adjustment.Direction.CREDIT))
        mm.adjustment_total = (Decimal(debits) - Decimal(credits)) if debits or credits else Decimal('0')

        mm.total_cost = mm.meal_cost + mm.guest_meal_cost

        approved_deposits = Deposit.objects.filter(month=month, member=mm.member, status=Deposit.Status.APPROVED)
        mm.approved_deposit_total = sum(d.amount for d in approved_deposits)

        mm.closing_balance = mm.opening_balance + mm.total_cost + mm.adjustment_total - mm.approved_deposit_total

        sum_member_costs += (mm.meal_cost + mm.guest_meal_cost)

    # e. residual
    residual = Decimal(total_expense) - sum_member_costs

    if residual != 0:
        # pick member with highest unit count
        members_sorted = sorted(members, key=lambda m: (-(m.meal_units + m.guest_meal_units), m.member.id))
        target = members_sorted[0]
        direction = Adjustment.Direction.DEBIT if residual > 0 else Adjustment.Direction.CREDIT
        adj = Adjustment.objects.create(
            month=month,
            member=target.member,
            direction=direction,
            amount=abs(residual),
            reason='Automatic rounding residual allocation at month close',
            created_by=None,
        )
        # fold into target's totals
        if direction == Adjustment.Direction.DEBIT:
            target.adjustment_total += adj.amount
            target.total_cost += adj.amount
            target.closing_balance += adj.amount
        else:
            target.adjustment_total -= adj.amount
            target.total_cost -= adj.amount
            target.closing_balance -= adj.amount
        target.save()

    # f. finalize_at
    now = timezone.now()
    for mm in members:
        mm.finalized_at = now
        mm.save()

    # g. set month fields
    month.final_meal_rate = final_meal_rate
    month.final_total_expense = total_expense
    month.rounding_residual = residual
    month.status = Month.Status.CLOSED
    month.closed_at = now
    month.closed_by = acting_user
    month.save()

    return {
        'countable_meal_units': countable_meal_units,
        'total_expense': total_expense,
        'final_meal_rate': final_meal_rate,
        'residual': residual,
    }
