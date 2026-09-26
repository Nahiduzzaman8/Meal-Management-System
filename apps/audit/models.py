from django.db import models

from apps.users.models import User


class AuditLog(models.Model):
    actor = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    action = models.CharField(max_length=128)
    entity_type = models.CharField(max_length=128)
    entity_id = models.BigIntegerField(null=True, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"AuditLog({self.action} by {self.actor})"
