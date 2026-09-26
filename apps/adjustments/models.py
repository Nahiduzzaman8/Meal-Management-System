from django.db import models
from django.db.models import Q

from apps.users.models import User
from apps.months.models import Month


class Adjustment(models.Model):
    class Direction(models.TextChoices):
        DEBIT = "DEBIT", "Debit"
        CREDIT = "CREDIT", "Credit"

    month = models.ForeignKey(Month, on_delete=models.PROTECT, related_name='adjustments')
    member = models.ForeignKey(User, on_delete=models.PROTECT, related_name='adjustments')
    direction = models.CharField(max_length=6, choices=Direction.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.TextField()
    source_entity_type = models.CharField(max_length=128, blank=True)
    source_entity_id = models.BigIntegerField(null=True, blank=True)
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.PROTECT, related_name='adjustments_created')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(amount__gt=0), name='adjustment_amount_positive'),
        ]

    def __str__(self):
        return f"Adjustment({self.member.username}, {self.direction}, {self.amount})"
