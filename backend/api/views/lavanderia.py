from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from ..access_control import LAVANDERIA_ROLES
from ..auth_decorator import token_required
from ..responses import error_response, success_response
from ..services import lavanderia_service


@csrf_exempt
@token_required(roles=LAVANDERIA_ROLES)
@require_http_methods(["GET"])
def consumo_lavanderia_categorias_view(request):
    try:
        categorias, error = lavanderia_service.listar_categorias(request)
        if error:
            return error
        return success_response(categorias)
    except Exception as exc:
        return error_response(str(exc), 'SERVER_ERROR', 500)


@csrf_exempt
@token_required(roles=LAVANDERIA_ROLES)
@require_http_methods(["GET"])
def consumo_lavanderia_servicos_view(request):
    try:
        servicos, error = lavanderia_service.listar_servicos(request)
        if error:
            return error
        return success_response(servicos)
    except Exception as exc:
        return error_response(str(exc), 'SERVER_ERROR', 500)


@csrf_exempt
@token_required(roles=LAVANDERIA_ROLES)
@require_http_methods(["GET", "POST"])
def consumo_lavanderia_ordens_view(request):
    return lavanderia_service.listar_ou_criar_ordens(request)


@csrf_exempt
@token_required(roles=LAVANDERIA_ROLES)
@require_http_methods(["POST"])
def consumo_lavanderia_ordem_status_view(request, ordem_id):
    return lavanderia_service.atualizar_status(request, ordem_id)
