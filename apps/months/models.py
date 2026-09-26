from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.users.models import User


class Month(models.Model):
    class Status(models.TextChoices):
        PLANNED = "PLANNED", "Planned"
        OPEN = "OPEN", "Open"
        CLOSED = "CLOSED", "Closed"

    name = models.CharField(max_length=128, unique=True)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PLANNED)
    final_meal_rate = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    final_total_expense = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    rounding_residual = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    closed_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='months_created')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(start_date__lt=models.F('end_date')), name='start_before_end'),
            models.UniqueConstraint(fields=['status'], condition=Q(status='OPEN'), name='unique_open_month'),
        ]

    def __str__(self):
        return self.name


class ManagerAssignment(models.Model):
    month = models.ForeignKey(Month, on_delete=models.CASCADE, related_name='manager_assignments')
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='manager_roles')
    assigned_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='+')
    assigned_at = models.DateTimeField(auto_now_add=True)
    unassigned_at = models.DateTimeField(null=True, blank=True)
    unassigned_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.PROTECT, related_name='+')

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['month'], condition=Q(unassigned_at=None), name='unique_active_manager_per_month')
        ]

    @classmethod
    def current_manager(cls, month: Month):
        try:
            ma = cls.objects.get(month=month, unassigned_at=None)
            return ma.user
        except cls.DoesNotExist:
            return None


class MonthMember(models.Model):
    month = models.ForeignKey(Month, on_delete=models.CASCADE, related_name='members')
    member = models.ForeignKey(User, on_delete=models.PROTECT, related_name='month_memberships')
    joined_on = models.DateField()
    left_on = models.DateField(null=True, blank=True)
    opening_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    lunch_count = models.PositiveIntegerField(default=0)
    dinner_count = models.PositiveIntegerField(default=0)
    meal_units = models.PositiveIntegerField(default=0)
    guest_lunch_count = models.PositiveIntegerField(default=0)
    guest_dinner_count = models.PositiveIntegerField(default=0)
    guest_meal_units = models.PositiveIntegerField(default=0)
    meal_rate_applied = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    meal_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    guest_meal_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    adjustment_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    approved_deposit_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    closing_balance = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    finalized_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('month', 'member')

    def __str__(self):
        return f"{self.member.username} @ {self.month.name}"
