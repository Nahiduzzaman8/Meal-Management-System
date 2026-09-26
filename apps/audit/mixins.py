from django.db import transaction

from apps.audit.models import AuditLog


class AuditLogMixin:
    """Write structured audit rows for creation/update/deletion actions."""

    def _write_audit(self, *, action, entity_type, entity_id=None, description=''):
        actor = getattr(self.request, 'user', None) if hasattr(self, 'request') else None
        AuditLog.objects.create(
            actor=actor,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            description=description,
        )

    def perform_create(self, obj, *, action, entity_type=None, description=None):
        if action:
            self._write_audit(
                action=action,
                entity_type=entity_type or obj.__class__.__name__,
                entity_id=getattr(obj, 'pk', None),
                description=description or f"Created {obj.__class__.__name__} #{getattr(obj, 'pk', 'new')}",
            )
        return obj

    def perform_update(self, obj, *, action, entity_type=None, description=None):
        if action:
            self._write_audit(
                action=action,
                entity_type=entity_type or obj.__class__.__name__,
                entity_id=getattr(obj, 'pk', None),
                description=description or f"Updated {obj.__class__.__name__} #{getattr(obj, 'pk', 'new')}",
            )
        return obj

    def perform_destroy(self, obj, *, action, entity_type=None, description=None):
        if action:
            self._write_audit(
                action=action,
                entity_type=entity_type or obj.__class__.__name__,
                entity_id=getattr(obj, 'pk', None),
                description=description or f"Deleted {obj.__class__.__name__} #{getattr(obj, 'pk', 'new')}",
            )
        return obj
