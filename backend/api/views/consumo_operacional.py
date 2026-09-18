from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from ..access_control import CONSUMO_CONTA_READ_ROLES, CONSUMO_ROLES
from ..auth_decorator import token_required
from ..responses import error_response, success_response
from ..services import consumo_service


@csrf_exempt
@token_required(roles=CONSUMO_CONTA_READ_ROLES)
@require_http_methods(["GET"])
def consumo_reservas_abertas_view(request):
    try:
        return success_response(consumo_service.buscar_reservas_abertas())
    except Exception as exc:
        return error_response(str(exc), 'SERVER_ERROR', 500)


@csrf_exempt
@token_required(roles=CONSUMO_ROLES)
@require_http_methods(["POST"])
def consumo_vendas_view(request):
    return consumo_service.criar_venda(request)


@csrf_exempt
@token_required(roles=CONSUMO_CONTA_READ_ROLES)
@require_http_methods(["GET"])
def consumo_conta_detail_view(request, conta_id):
    try:
        conta = consumo_service.buscar_conta_detalhe(conta_id)
        if not conta:
            return error_response('Conta de consumo nao encontrada.', 'NOT_FOUND', 404)
        return success_response(conta)
    except Exception as exc:
        return error_response(str(exc), 'SERVER_ERROR', 500)


@csrf_exempt
@token_required(roles=CONSUMO_ROLES)
@require_http_methods(["POST"])
def consumo_fechar_conta_view(request, conta_id):
    try:
        return consumo_service.fechar_conta(conta_id)
    except Exception as exc:
        return error_response(str(exc), 'SERVER_ERROR', 500)
