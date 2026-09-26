from django.db import models
from django.db.models import Q

from apps.users.models import User
from apps.months.models import Month


class GuestMeal(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    member = models.ForeignKey(User, on_delete=models.PROTECT, related_name='guest_meals')
    month = models.ForeignKey(Month, on_delete=models.PROTECT, related_name='guest_meals')
    meal_date = models.DateField()
    lunch_quantity = models.PositiveIntegerField(default=0)
    dinner_quantity = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    rejection_reason = models.TextField(blank=True)
    remarks = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    processed_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.PROTECT, related_name='+')

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(lunch_quantity__gt=0) | Q(dinner_quantity__gt=0), name='guest_meal_has_quantity'),
            models.UniqueConstraint(fields=['member', 'meal_date'], condition=~Q(status='REJECTED'), name='unique_active_guest_meal_per_date'),
        ]

    def __str__(self):
        return f"GuestMeal({self.member.username}, {self.meal_date})"
