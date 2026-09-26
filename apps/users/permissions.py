ROLE_CAPABILITIES = {
    "ADMIN": {
        "month.create", "month.open", "month.close",
        "manager.assign",
        "user.create", "user.view", "user.deactivate", "user.reset_password",
        "settings.manage", "adjustment.create", "audit.view",
    },
    "MEMBER": {
        "meal.submit", "meal.view_own",
        "deposit.submit", "deposit.view_own",
        "guest_meal.submit", "guest_meal.view_own",
        "report.view_own",
    },
}

MANAGER_CAPABILITIES = {
    "meal.view_all",
    "deposit.approve",
    "guest_meal.approve",
    "expense.create", "expense.update", "expense.delete",
    "report.view_all",
    "month.view",
}

# Add month.view to ADMIN role as well
ROLE_CAPABILITIES['ADMIN'].add('month.view')

from rest_framework.permissions import BasePermission


class HasCapability(BasePermission):
    """DRF permission that checks `view.required_capability` on the view.

    If the view does not define `required_capability`, this permission
    allows access (it is permissive so views can layer it with
    `IsAuthenticated` when needed).
    """

    def has_permission(self, request, view):
        code = getattr(view, 'required_capability', None)
        if code is None:
            return True
        user = request.user
        if not getattr(user, 'is_authenticated', False):
            return False
        return user.has_capability(code)
