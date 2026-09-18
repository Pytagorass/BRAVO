import json

from django.db import IntegrityError
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from ..access_control import FULL_ACCESS_ROLES, RESERVA_SUPPORT_READ_ROLES
from ..auth_decorator import token_required
from ..models import Quarto
from ..responses import error_response, success_response


STATUS_QUARTO_VALIDOS = ('Dispon\u00edvel', 'Manuten\u00e7\u00e3o')


def _quarto_to_dict(quarto):
    return {
        'id_quarto': quarto.id_quarto,
        'numero': quarto.numero,
        'tipo_quarto': quarto.tipo_quarto,
        'valor_diaria': float(quarto.valor_diaria),
        'status_quarto': quarto.status_quarto,
    }


@csrf_exempt
@token_required(method_roles={'GET': RESERVA_SUPPORT_READ_ROLES, 'POST': FULL_ACCESS_ROLES})
@require_http_methods(["GET", "POST"])
def quartos_view(request):
    if request.method == 'GET':
        status = request.GET.get('status', 'Dispon\u00edvel')
        if status not in STATUS_QUARTO_VALIDOS:
            status = 'Dispon\u00edvel'

        try:
            quartos = Quarto.objects.filter(status_quarto=status).order_by('numero')
            return success_response([_quarto_to_dict(quarto) for quarto in quartos])
        except Exception as exc:
            return error_response(str(exc), 'SERVER_ERROR', 500)

    try:
        data = json.loads(request.body or '{}')
        quarto = Quarto.objects.create(
            numero=data.get('numero'),
            valor_diaria=data.get('valor_diaria'),
            tipo_quarto=data.get('tipo_quarto'),
            status_quarto=data.get('status_quarto', 'Dispon\u00edvel'),
        )
        return success_response(_quarto_to_dict(quarto), 'QUARTO_CREATED', 201)
    except IntegrityError as exc:
        if 'quarto_numero_key' in str(exc):
            return error_response(
                f'Erro: O numero de quarto "{data.get("numero")}" ja esta cadastrado.',
                'CONFLICT',
                409,
            )
        return error_response(f'Erro de integridade: {str(exc)}', 'DB_INTEGRITY_ERROR', 400)
    except Exception as exc:
        return error_response(str(exc), 'SERVER_ERROR', 500)


@csrf_exempt
@token_required(method_roles={'GET': RESERVA_SUPPORT_READ_ROLES, 'PUT': FULL_ACCESS_ROLES, 'DELETE': FULL_ACCESS_ROLES})
@require_http_methods(["GET", "PUT", "DELETE"])
def quarto_detail_view(request, quarto_id):
    if request.method == 'GET':
        try:
            quarto = Quarto.objects.get(pk=quarto_id)
            return success_response(_quarto_to_dict(quarto))
        except Quarto.DoesNotExist:
            return error_response('Quarto nao encontrado.', 'NOT_FOUND', 404)
        except Exception as exc:
            return error_response(str(exc), 'SERVER_ERROR', 500)

    if request.method == 'PUT':
        try:
            data = json.loads(request.body or '{}')
            numero = data.get('numero')
            valor_diaria = data.get('valor_diaria')
            tipo_quarto = data.get('tipo_quarto')
            status_quarto = data.get('status_quarto')

            if not numero or not valor_diaria or not tipo_quarto or not status_quarto:
                return error_response('Todos os campos sao obrigatorios.', 'VALIDATION_ERROR', 400)

            if status_quarto not in STATUS_QUARTO_VALIDOS:
                return error_response(
                    f"Status '{status_quarto}' invalido. Use 'Disponivel' ou 'Manutencao'.",
                    'VALIDATION_ERROR',
                    400,
                )

            quarto = Quarto.objects.get(pk=quarto_id)
            quarto.numero = numero
            quarto.valor_diaria = valor_diaria
            quarto.tipo_quarto = tipo_quarto
            quarto.status_quarto = status_quarto
            quarto.save(
                update_fields=[
                    'numero',
                    'valor_diaria',
                    'tipo_quarto',
                    'status_quarto',
                ]
            )

            return success_response(_quarto_to_dict(quarto), 'QUARTO_UPDATED')
        except Quarto.DoesNotExist:
            return error_response('Quarto nao encontrado com este ID.', 'NOT_FOUND', 404)
        except IntegrityError as exc:
            if 'quarto_numero_key' in str(exc):
                return error_response(
                    f'Erro: O numero de quarto "{numero}" ja esta cadastrado.',
                    'CONFLICT',
                    409,
                )
            return error_response(f'Erro de integridade: {str(exc)}', 'DB_INTEGRITY_ERROR', 400)
        except Exception as exc:
            return error_response(str(exc), 'SERVER_ERROR', 500)

    try:
        deleted, _ = Quarto.objects.filter(pk=quarto_id).delete()
        if deleted == 0:
            return error_response('Quarto nao encontrado com este ID.', 'NOT_FOUND', 404)

        return success_response(None, 'QUARTO_DELETED', 204)
    except IntegrityError:
        return error_response(
            'Nao e possivel excluir este quarto pois ele esta vinculado a uma ou mais reservas.',
            'FK_CONSTRAINT',
            409,
        )
    except Exception as exc:
        return error_response(str(exc), 'SERVER_ERROR', 500)
