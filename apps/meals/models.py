from django.db import models

from apps.users.models import User
from apps.months.models import Month


class Meal(models.Model):
    member = models.ForeignKey(User, on_delete=models.PROTECT, related_name='meals')
    month = models.ForeignKey(Month, on_delete=models.PROTECT, related_name='meals')
    meal_date = models.DateField()
    lunch = models.BooleanField(default=False)
    dinner = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('member', 'meal_date')

    # NOTE: month resolution happens server-side (serializer); do not
    # trust client-supplied month values when creating Meal instances.

    def __str__(self):
        return f"Meal({self.member.username}, {self.meal_date})"
