from django.db import models
from django.db.models import Q

from apps.users.models import User
from apps.months.models import Month


class ExpenseQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_deleted=False)


class ExpenseManager(models.Manager):
    def get_queryset(self):
        return ExpenseQuerySet(self.model, using=self._db).filter(is_deleted=False)


class ExpenseAllManager(models.Manager):
    def get_queryset(self):
        return ExpenseQuerySet(self.model, using=self._db)


class Expense(models.Model):
    CATEGORY_CHOICES = [
        ("Grocery", "Grocery"),
        ("Gas", "Gas"),
        ("Electricity", "Electricity"),
        ("Water", "Water"),
        ("Internet", "Internet"),
        ("Cleaning", "Cleaning"),
        ("Maintenance", "Maintenance"),
        ("Others", "Others"),
    ]

    month = models.ForeignKey(Month, on_delete=models.PROTECT, related_name='expenses')
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='expenses_created')
    category = models.CharField(max_length=32, choices=CATEGORY_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    expense_date = models.DateField()
    description = models.TextField()
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.PROTECT, related_name='+')
    delete_reason = models.TextField(blank=True)

    objects = ExpenseManager()
    all_objects = ExpenseAllManager()

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(amount__gt=0), name='expense_amount_positive'),
        ]

    def __str__(self):
        return f"Expense({self.category}, {self.amount})"
