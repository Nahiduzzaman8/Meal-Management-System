from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _

from apps.users.permissions import ROLE_CAPABILITIES, MANAGER_CAPABILITIES


class User(AbstractUser):
    class Roles(models.TextChoices):
        ADMIN = "ADMIN", _("Admin")
        MEMBER = "MEMBER", _("Member")

    role = models.CharField(max_length=10, choices=Roles.choices, default=Roles.MEMBER)
    phone = models.CharField(max_length=32, blank=True)
    must_change_password = models.BooleanField(default=True)

    def deactivate(self):
        """Deactivate the user and blacklist all outstanding refresh tokens."""
        self.is_active = False
        self.save()
        try:
            from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
            for ot in OutstandingToken.objects.filter(user=self):
                BlacklistedToken.objects.get_or_create(token=ot)
        except Exception:
            # Token blacklist app may not be available in some test contexts.
            pass

    def has_capability(self, code: str) -> bool:
        """Check capability for the user.

        Rules:
        - `is_superuser` always returns True.
        - Users inherit capabilities from `ROLE_CAPABILITIES[self.role]`.
        - Users gain `MANAGER_CAPABILITIES` if they are the active
          manager for the currently OPEN month (via
          `months.ManagerAssignment.current_manager`).
        - ADMIN role also implicitly has manager capabilities.
        """
        if self.is_superuser:
            return True

        role_caps = ROLE_CAPABILITIES.get(self.role, set())

        if self.role == 'ADMIN':
            return code in role_caps or code in MANAGER_CAPABILITIES

        if code in role_caps:
            return True

        try:
            from apps.months.models import Month, ManagerAssignment
            open_month = Month.objects.filter(status=Month.Status.OPEN).first()
            if open_month is None:
                return False

            current = ManagerAssignment.current_manager(open_month)
            if current and current.pk == self.pk:
                return code in MANAGER_CAPABILITIES
        except Exception:
            return False

        return False

    # NOTE: `username` must never be editable after creation. Enforce in serializer.
