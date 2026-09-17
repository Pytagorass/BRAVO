import datetime
import json

from django.db import IntegrityError
from django.db.models import Exists, OuterRef
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from ..access_control import FULL_ACCESS_ROLES, OPERACAO_READ_ROLES
from ..auth_decorator import token_required
from ..models import Barco, Reserva, TipoPasseio
from ..responses import error_response, success_response


STATUS_BARCO_VALIDOS = ('Dispon\u00edvel', 'Manuten\u00e7\u00e3o', 'Bloqueado')


def _barco_to_dict(barco, incluir_periodo=False):
    data = {
        'id_barco': barco.id_barco,
        'nome_barco': barco.nome_barco,
        'capacidade_pessoas': barco.capacidade_pessoas,
        'status_barco': barco.status_barco,
        'observacao': barco.observacao,
        'dt_criacao': barco.dt_criacao,
        'disponivel_periodo': True,
    }
    if incluir_periodo:
        data['reservas_no_periodo'] = 0
    return data


def _tipo_passeio_to_dict(tipo):
    return {
        'id_tipo_passeio': tipo.id_tipo_passeio,
        'nome_tipo': tipo.nome_tipo,
        'descricao': tipo.descricao,
        'ativo': tipo.ativo,
    }


def _validar_barco_payload(data):
    nome_barco = (data.get('nome_barco') or '').strip()
    status_barco = data.get('status_barco') or 'Dispon\u00edvel'
    observacao = data.get('observacao')

    if not nome_barco:
        return None, error_response('Nome do barco e obrigatorio.', 'VALIDATION_ERROR', 400)

    try:
        capacidade_pessoas = int(data.get('capacidade_pessoas'))
    except (TypeError, ValueError):
        return None, error_response('Capacidade deve ser um numero inteiro.', 'VALIDATION_ERROR', 400)

    if capacidade_pessoas <= 0:
        return None, error_response('Capacidade deve ser maior que zero.', 'VALIDATION_ERROR', 400)

    if status_barco not in STATUS_BARCO_VALIDOS:
        return None, error_response('Status de barco invalido.', 'VALIDATION_ERROR', 400)

    return {
        'nome_barco': nome_barco,
        'capacidade_pessoas': capacidade_pessoas,
        'status_barco': status_barco,
        'observacao': observacao.strip() if isinstance(observacao, str) and observacao.strip() else None,
    }, None


def _parse_periodo(request):
    data_embarque = request.GET.get('data_embarque')
    data_desembarque = request.GET.get('data_desembarque')

    if not data_embarque and not data_desembarque:
        return None, None

    if not data_embarque or not data_desembarque:
        return None, error_response(
            'Informe data_embarque e data_desembarque para filtrar disponibilidade.',
            'DATAS_OPERACAO_INVALIDAS',
            400,
        )

    try:
        embarque = datetime.datetime.strptime(data_embarque, '%Y-%m-%d').date()
        desembarque = datetime.datetime.strptime(data_desembarque, '%Y-%m-%d').date()
    except (TypeError, ValueError):
        return None, error_response('Formato de data invalido. Use YYYY-MM-DD.', 'DATAS_OPERACAO_INVALIDAS', 400)

    if desembarque < embarque:
        return None, error_response(
            'Data de desembarque deve ser igual ou posterior ao embarque.',
            'DATAS_OPERACAO_INVALIDAS',
            400,
        )

    return (embarque, desembarque), None


@csrf_exempt
@token_required(method_roles={'GET': OPERACAO_READ_ROLES, 'POST': FULL_ACCESS_ROLES})
@require_http_methods(["GET", "POST"])
def barcos_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body or '{}')
            payload, error = _validar_barco_payload(data)
            if error:
                return error

            barco = Barco.objects.create(**payload)
            return success_response(_barco_to_dict(barco), 'BARCO_CREATED', 201)
        except IntegrityError as exc:
            if 'barco_nome_barco_key' in str(exc):
                return error_response(
                    f'Barco "{data.get("nome_barco")}" ja esta cadastrado.',
                    'CONFLICT',
                    409,
                )
            return error_response(f'Erro de integridade: {str(exc)}', 'DB_INTEGRITY_ERROR', 400)
        except Exception as exc:
            return error_response(str(exc), 'SERVER_ERROR', 500)

    status = request.GET.get('status')
    periodo, error = _parse_periodo(request)
    if error:
        return error

    reserva_id = request.GET.get('reserva_id')
    try:
        reserva_id = int(reserva_id) if reserva_id not in (None, '') else None
    except (TypeError, ValueError):
        return error_response('reserva_id invalido.', 'VALIDATION_ERROR', 400)

    try:
        barcos = Barco.objects.all().order_by('nome_barco')

        if status:
            if status == 'Todos':
                status = None
            elif status not in STATUS_BARCO_VALIDOS:
                return error_response('Status de barco invalido.', 'VALIDATION_ERROR', 400)
            else:
                barcos = barcos.filter(status_barco=status)

        if periodo:
            embarque, desembarque = periodo
            conflitos = Reserva.objects.filter(
                barco_id=OuterRef('pk'),
                data_embarque__isnull=False,
                data_desembarque__isnull=False,
                data_embarque__lte=desembarque,
                data_desembarque__gte=embarque,
            ).exclude(status_reserva='Cancelada')

            if reserva_id is not None:
                conflitos = conflitos.exclude(pk=reserva_id)

            barcos = barcos.annotate(tem_conflito=Exists(conflitos)).filter(tem_conflito=False)

        return success_response([_barco_to_dict(barco, bool(periodo)) for barco in barcos])
    except Exception as exc:
        return error_response(str(exc), 'SERVER_ERROR', 500)


@csrf_exempt
@token_required(method_roles={'GET': OPERACAO_READ_ROLES, 'PUT': FULL_ACCESS_ROLES, 'DELETE': FULL_ACCESS_ROLES})
@require_http_methods(["GET", "PUT", "DELETE"])
def barco_detail_view(request, barco_id):
    if request.method == 'GET':
        try:
            barco = Barco.objects.get(pk=barco_id)
            return success_response(_barco_to_dict(barco))
        except Barco.DoesNotExist:
            return error_response('Barco nao encontrado.', 'NOT_FOUND', 404)
        except Exception as exc:
            return error_response(str(exc), 'SERVER_ERROR', 500)

    if request.method == 'PUT':
        try:
            data = json.loads(request.body or '{}')
            payload, error = _validar_barco_payload(data)
            if error:
                return error

            barco = Barco.objects.get(pk=barco_id)
            for field, value in payload.items():
                setattr(barco, field, value)
            barco.save(update_fields=['nome_barco', 'capacidade_pessoas', 'status_barco', 'observacao'])

            return success_response(_barco_to_dict(barco), 'BARCO_UPDATED')
        except Barco.DoesNotExist:
            return error_response('Barco nao encontrado.', 'NOT_FOUND', 404)
        except IntegrityError as exc:
            if 'barco_nome_barco_key' in str(exc):
                return error_response(
                    f'Barco "{data.get("nome_barco")}" ja esta cadastrado.',
                    'CONFLICT',
                    409,
                )
            return error_response(f'Erro de integridade: {str(exc)}', 'DB_INTEGRITY_ERROR', 400)
        except Exception as exc:
            return error_response(str(exc), 'SERVER_ERROR', 500)

    try:
        deleted, _ = Barco.objects.filter(pk=barco_id).delete()
        if deleted == 0:
            return error_response('Barco nao encontrado.', 'NOT_FOUND', 404)

        return success_response(None, 'BARCO_DELETED', 204)
    except IntegrityError:
        return error_response(
            'Nao e possivel excluir este barco pois ele esta vinculado a uma ou mais reservas.',
            'FK_CONSTRAINT',
            409,
        )
    except Exception as exc:
        return error_response(str(exc), 'SERVER_ERROR', 500)


@csrf_exempt
@token_required(roles=OPERACAO_READ_ROLES)
@require_http_methods(["GET"])
def tipos_passeio_view(request):
    ativo = request.GET.get('ativo', 'Ativo')
    if ativo not in ['Ativo', 'Inativo', 'Todos']:
        ativo = 'Ativo'

    try:
        tipos = TipoPasseio.objects.all().order_by('nome_tipo')
        if ativo != 'Todos':
            tipos = tipos.filter(ativo=ativo)

        return success_response([_tipo_passeio_to_dict(tipo) for tipo in tipos])
    except Exception as exc:
        return error_response(str(exc), 'SERVER_ERROR', 500)
