from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from ..access_control import GESTAO_ROLES
from ..auth_decorator import token_required
from ..responses import error_response, success_response
from ..services import gestao_service


@csrf_exempt
@token_required(roles=GESTAO_ROLES)
@require_http_methods(["GET"])
def get_indicadores_gestao(request):
    try:
        return success_response(gestao_service.buscar_indicadores(request))
    except Exception as exc:
        return error_response(str(exc), 'SERVER_ERROR', 500)


@csrf_exempt
@token_required(roles=GESTAO_ROLES)
@require_http_methods(["GET"])
def get_reservas_pendentes(request):
    try:
        return success_response(gestao_service.buscar_reservas_pendentes())
    except Exception as exc:
        return error_response(str(exc), 'ERRO_INTERNO', 500)
