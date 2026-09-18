from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from ..access_control import RECEPCAO_ROLES, RESERVAS_READ_ROLES, RESERVAS_ROLES
from ..auth_decorator import token_required
from ..responses import error_response, success_response
from ..services import reserva_service


@csrf_exempt
@token_required(roles=RESERVAS_ROLES)
@require_http_methods(["POST"])
def reservas_view(request):
    return reserva_service.criar_reserva(request)


@csrf_exempt
@token_required(roles=RESERVAS_READ_ROLES)
@require_http_methods(["GET"])
def get_agenda_reservas(request):
    try:
        return success_response(reserva_service.listar_agenda())
    except Exception as exc:
        return error_response(str(exc), 'SERVER_ERROR', 500)


@csrf_exempt
@token_required(roles=RESERVAS_READ_ROLES)
@require_http_methods(["GET"])
def get_reserva_detalhes(request, reserva_quarto_id):
    try:
        detalhes = reserva_service.buscar_detalhes(reserva_quarto_id)
        if not detalhes:
            return error_response('Reserva não encontrada', 'NOT_FOUND', 404)

        return success_response(detalhes)
    except Exception as exc:
        return error_response(str(exc), 'SERVER_ERROR', 500)


@csrf_exempt
@token_required(roles=RECEPCAO_ROLES)
@require_http_methods(["PATCH"])
def update_reserva_status_view(request, reserva_quarto_id):
    try:
        return reserva_service.atualizar_status(request, reserva_quarto_id)
    except Exception as exc:
        return error_response(str(exc), 'SERVER_ERROR', 500)


@csrf_exempt
@token_required(roles=RESERVAS_ROLES)
@require_http_methods(["PUT"])
def edit_reserva_view(request, reserva_quarto_id):
    return reserva_service.editar_reserva(request, reserva_quarto_id)
