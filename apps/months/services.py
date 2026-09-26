from django.db import transaction
from django.utils import timezone
from decimal import Decimal

from apps.months.models import ManagerAssignment, Month, MonthMember
from apps.users.models import User
from apps.months.calculations import finalize_month


def create_month(name, start_date, end_date, created_by):
    if start_date >= end_date:
        raise ValueError('start_date must be before end_date')
    # check overlap
    overlaps = Month.objects.filter(start_date__lte=end_date, end_date__gte=start_date).exists()
    if overlaps:
        raise ValueError('Month date range overlaps with existing month')
    return Month.objects.create(name=name, start_date=start_date, end_date=end_date, status=Month.Status.PLANNED, created_by=created_by)


def open_month(month_id, acting_user):
    with transaction.atomic():
        month = Month.objects.select_for_update().get(pk=month_id)
        if month.status != Month.Status.PLANNED:
            raise ValueError('Only PLANNED months may be opened')
        # check no other open month
        if Month.objects.filter(status=Month.Status.OPEN).exclude(pk=month.pk).exists():
            raise ValueError('Another month is already OPEN')

        month.status = Month.Status.OPEN
        month.save()

        today = timezone.now().date()
        # create MonthMember for all active members
        members = User.objects.filter(is_active=True, role=User.Roles.MEMBER)
        for m in members:
            # find most recent closed month member closing_balance
            prev = MonthMember.objects.filter(member=m, month__status=Month.Status.CLOSED).order_by('-month__end_date').first()
            opening = prev.closing_balance if prev and prev.closing_balance is not None else Decimal('0')
            MonthMember.objects.create(month=month, member=m, joined_on=today, opening_balance=opening)

        return month


def assign_manager(month, target_user, assigned_by):
    if not isinstance(target_user, User):
        raise ValueError('Target user is invalid.')

    if not target_user.is_active:
        raise ValueError('Target user must be active to become manager.')

    if target_user.role != User.Roles.MEMBER:
        raise ValueError('Only active MEMBER users can be assigned as month manager.')

    current = ManagerAssignment.current_manager(month)
    if current and current.pk == target_user.pk:
        raise ValueError('Target user is already the active manager for this month.')

    with transaction.atomic():
        month = Month.objects.select_for_update().get(pk=month.pk)
        active_assignment = ManagerAssignment.objects.select_for_update().filter(month=month, unassigned_at__isnull=True).first()
        if active_assignment is not None:
            active_assignment.unassigned_at = timezone.now()
            active_assignment.unassigned_by = assigned_by
            active_assignment.save(update_fields=['unassigned_at', 'unassigned_by'])

        assignment = ManagerAssignment.objects.create(
            month=month,
            user=target_user,
            assigned_by=assigned_by,
        )
        return assignment


def close_month(month_id, acting_user):
    with transaction.atomic():
        month = Month.objects.select_for_update().get(pk=month_id)

        failures = []
        if month.status != Month.Status.OPEN:
            failures.append('month_not_open')

        # pending deposits
        from apps.deposits.models import Deposit
        if Deposit.objects.filter(month=month, status=Deposit.Status.PENDING).exists():
            failures.append('pending_deposits')

        from apps.guest_meals.models import GuestMeal
        if GuestMeal.objects.filter(month=month, status=GuestMeal.Status.PENDING).exists():
            failures.append('pending_guest_meals')

        from apps.meals.models import Meal
        member_units = Meal.objects.filter(month=month)
        total_member_units = sum((1 if m.lunch else 0) + (1 if m.dinner else 0) for m in member_units)

        from apps.expenses.models import Expense
        total_expense = sum(e.amount for e in Expense.all_objects.filter(month=month, is_deleted=False))

        if total_member_units + sum((g.lunch_quantity + g.dinner_quantity) for g in GuestMeal.objects.filter(month=month, status=GuestMeal.Status.APPROVED)) <= 0:
            failures.append('no_countable_meal_units')

        if not Expense.all_objects.filter(month=month, is_deleted=False).exists():
            failures.append('no_expenses')

        if not MonthMember.objects.filter(month=month, left_on__isnull=True).exists():
            failures.append('no_active_members')

        from apps.months.models import ManagerAssignment
        if not ManagerAssignment.objects.filter(month=month, unassigned_at__isnull=True).exists():
            failures.append('no_active_manager')

        if failures:
            return {'code': 'month_close_blocked', 'failures': failures}

        # perform finalize
        result = finalize_month(month, acting_user=acting_user)
        return {'status': 'closed', 'summary': result}
