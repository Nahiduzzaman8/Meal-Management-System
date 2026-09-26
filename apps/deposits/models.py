from django.db import models
from django.db.models import Q

from apps.users.models import User
from apps.months.models import Month


class Deposit(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    member = models.ForeignKey(User, on_delete=models.PROTECT, related_name='deposits')
    month = models.ForeignKey(Month, on_delete=models.PROTECT, related_name='deposits')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    class PaymentMethod(models.TextChoices):
        CASH = "CASH", "Cash"
        BKASH = "BKASH", "Bkash"
        NAGAD = "NAGAD", "Nagad"
        BANK = "BANK", "Bank"

    payment_method = models.CharField(max_length=10, choices=PaymentMethod.choices)
    transaction_reference = models.CharField(max_length=128, blank=True)
    payment_date = models.DateField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    rejection_reason = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    processed_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.PROTECT, related_name='+')

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(amount__gt=0), name='deposit_amount_positive'),
        ]

    def __str__(self):
        return f"Deposit({self.member.username}, {self.amount})"
