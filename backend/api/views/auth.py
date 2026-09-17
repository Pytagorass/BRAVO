from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from ..services import auth_service


@csrf_exempt
@require_http_methods(["POST"])
def login_view(request):
    return auth_service.login(request)


@csrf_exempt
@require_http_methods(["POST"])
def refresh_token_view(request):
    return auth_service.refresh_token(request)
