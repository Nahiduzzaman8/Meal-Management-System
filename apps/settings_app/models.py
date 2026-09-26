from django.db import models


class SystemSetting(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1)
    mess_name = models.CharField(max_length=128, default='My Mess')
    meal_submission_deadline = models.TimeField(null=True, blank=True)
    timezone = models.CharField(max_length=64, default='Asia/Dhaka')
    currency = models.CharField(max_length=8, default='BDT')

    def save(self, *args, **kwargs):
        self.id = 1
        super().save(*args, **kwargs)

    def __str__(self):
        return self.mess_name
