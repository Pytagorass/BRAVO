import json

from django.db import IntegrityError
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from ..access_control import RECEPCAO_ROLES
from ..auth_decorator import token_required
from ..models import Hospede
from ..responses import error_response, success_response


STATUS_HOSPEDE_VALIDOS = ('Ativo', 'Inativo')


def _is_valid_cpf(value):
    if not value:
        return False

    digits = ''.join(filter(str.isdigit, value))
    if len(digits) != 11 or digits == digits[0] * 11:
        return False

    def calc_digit(slice_len):
        total = sum(
            int(digits[i]) * ((slice_len + 2) - (i + 1))
            for i in range(slice_len)
        )
        rest = (total * 10) % 11
        return 0 if rest == 10 else rest

    return calc_digit(9) == int(digits[9]) and calc_digit(10) == int(digits[10])


def _validar_hospede_payload(data):
    pais_origem = data.get('pais_origem', 'Brasil')
    cpf = data.get('cpf')
    passaporte = data.get('passaporte')

    if pais_origem == 'Brasil':
        if not cpf:
            return error_response('CPF e obrigatorio para hospedes do Brasil.', 'VALIDATION_ERROR', 400)
        if not _is_valid_cpf(cpf):
            return error_response('Informe um CPF valido.', 'VALIDATION_ERROR', 400)
    elif not passaporte:
        return error_response('Passaporte e obrigatorio para hospedes estrangeiros.', 'VALIDATION_ERROR', 400)

    return None


def _hospede_to_dict(hospede):
    return {
        'id_hospede': hospede.id_hospede,
        'nome_hospede': hospede.nome_hospede,
        'email_hospede': hospede.email_hospede,
        'telefone': hospede.telefone,
        'pais_origem': hospede.pais_origem,
        'cpf': hospede.cpf,
        'passaporte': hospede.passaporte,
        'ativo': hospede.ativo,
    }


@csrf_exempt
@token_required(roles=RECEPCAO_ROLES)
@require_http_methods(["GET", "POST"])
def hospedes_view(request):
    if request.method == 'GET':
        status = request.GET.get('status', 'Ativo')
        if status not in STATUS_HOSPEDE_VALIDOS:
            status = 'Ativo'

        try:
            hospedes = Hospede.objects.filter(ativo=status).order_by('nome_hospede')
            return success_response([_hospede_to_dict(hospede) for hospede in hospedes])
        except Exception as exc:
            return error_response(str(exc), 'SERVER_ERROR', 500)

    try:
        data = json.loads(request.body or '{}')
        payload_error = _validar_hospede_payload(data)
        if payload_error:
            return payload_error

        hospede = Hospede.objects.create(
            nome_hospede=data.get('nome_hospede'),
            email_hospede=data.get('email_hospede'),
            telefone=data.get('telefone'),
            pais_origem=data.get('pais_origem', 'Brasil'),
            cpf=data.get('cpf'),
            passaporte=data.get('passaporte'),
        )
        return success_response(_hospede_to_dict(hospede), 'HOSPEDE_CREATED', 201)
    except IntegrityError as exc:
        return error_response(f'Erro de integridade: {str(exc)}', 'DB_INTEGRITY_ERROR', 400)
    except Exception as exc:
        return error_response(str(exc), 'SERVER_ERROR', 500)


@csrf_exempt
@token_required(roles=RECEPCAO_ROLES)
@require_http_methods(["PUT", "DELETE", "PATCH"])
def hospede_detail_view(request, hospede_id):
    if request.method == 'PUT':
        try:
            data = json.loads(request.body or '{}')
            payload_error = _validar_hospede_payload(data)
            if payload_error:
                return payload_error

            hospede = Hospede.objects.get(pk=hospede_id)
            hospede.nome_hospede = data.get('nome_hospede')
            hospede.email_hospede = data.get('email_hospede')
            hospede.telefone = data.get('telefone')
            hospede.pais_origem = data.get('pais_origem', 'Brasil')
            hospede.cpf = data.get('cpf')
            hospede.passaporte = data.get('passaporte')
            hospede.save(
                update_fields=[
                    'nome_hospede',
                    'email_hospede',
                    'telefone',
                    'pais_origem',
                    'cpf',
                    'passaporte',
                ]
            )

            return success_response(_hospede_to_dict(hospede), 'HOSPEDE_UPDATED')
        except Hospede.DoesNotExist:
            return error_response('Cliente nao encontrado.', 'NOT_FOUND', 404)
        except IntegrityError as exc:
            return error_response(f'Erro de integridade: {str(exc)}', 'DB_INTEGRITY_ERROR', 400)
        except Exception as exc:
            return error_response(str(exc), 'SERVER_ERROR', 500)

    if request.method == 'DELETE':
        try:
            updated = Hospede.objects.filter(pk=hospede_id).update(ativo='Inativo')
            if updated == 0:
                return error_response('Cliente nao encontrado com este ID.', 'NOT_FOUND', 404)

            return success_response(None, 'HOSPEDE_INACTIVATED', 204)
        except IntegrityError:
            return error_response(
                'Nao e possivel inativar este hospede (erro de integridade).',
                'FK_CONSTRAINT',
                409,
            )
        except Exception as exc:
            return error_response(str(exc), 'SERVER_ERROR', 500)

    try:
        data = json.loads(request.body or '{}')
        novo_status = data.get('ativo')
        if novo_status not in STATUS_HOSPEDE_VALIDOS:
            return error_response(
                "Status invalido. Envie 'Ativo' ou 'Inativo'.",
                'VALIDATION_ERROR',
                400,
            )

        updated = Hospede.objects.filter(pk=hospede_id).update(ativo=novo_status)
        if updated == 0:
            return error_response('Cliente nao encontrado.', 'NOT_FOUND', 404)

        return success_response(None, 'STATUS_UPDATED', 200)
    except Exception as exc:
        return error_response(str(exc), 'SERVER_ERROR', 500)
