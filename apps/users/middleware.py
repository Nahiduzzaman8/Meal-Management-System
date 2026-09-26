from django.http import JsonResponse
from django.urls import resolve


ALLOWED_WHILE_MUST_CHANGE = {
    'auth-me': 'GET',
    'auth-password-change': 'POST',
    'auth-logout': 'POST',
}


class MustChangePasswordMiddleware:
    """Reject requests when `request.user.must_change_password` is True,
    except for a small whitelist of auth endpoints.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Allow unauthenticated requests to pass through auth views
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return self.get_response(request)

        if getattr(request.user, 'must_change_password', False):
            try:
                resolver = resolve(request.path_info)
                name = resolver.url_name
            except Exception:
                name = None

            allowed_method = ALLOWED_WHILE_MUST_CHANGE.get(name)
            if allowed_method is None or request.method != allowed_method:
                return JsonResponse({'code': 'password_change_required', 'message': 'Password change required'}, status=403)

        return self.get_response(request)
