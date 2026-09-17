import datetime
import json

from django.db import IntegrityError, connection, transaction

from ..repositories import reserva_repository
from ..responses import error_response, success_response


STATUS_OPERACIONAL_VALIDOS = ('A Preparar', 'Pronto', 'Em Viagem', 'Finalizado')


def listar_agenda():
    return reserva_repository.buscar_agenda_reservas()


def buscar_detalhes(reserva_quarto_id):
    return reserva_repository.buscar_reserva_detalhes(reserva_quarto_id)


def _parse_json_body(request):
    try:
        return json.loads(request.body or '{}'), None
    except json.JSONDecodeError:
        return None, error_response('JSON invalido.', 'INVALID_JSON', 400)


def _parse_required_int(data, field_name, message, code='VALIDATION_ERROR'):
    try:
        value = data.get(field_name)
        if value in (None, ''):
            raise ValueError
        return int(value), None
    except (TypeError, ValueError):
        return None, error_response(message, code, 400)


def _parse_required_date(data, field_name, message):
    value = data.get(field_name)
    if not value:
        return None, error_response(message, 'DATAS_OPERACAO_INVALIDAS', 400)

    try:
        return datetime.datetime.strptime(value, '%Y-%m-%d').date(), None
    except (TypeError, ValueError):
        return None, error_response('Formato de data invalido. Use YYYY-MM-DD.', 'DATAS_OPERACAO_INVALIDAS', 400)


def _parse_data_estadia(data):
    checkin = data.get('checkin')
    checkout = data.get('checkout')
    if not checkin or not checkout:
        return None, None, error_response('Datas de check-in e check-out sao obrigatorias.', 'DATAS_INVALIDAS', 400)

    try:
        checkin_date = datetime.datetime.strptime(checkin, '%Y-%m-%d').date()
        checkout_date = datetime.datetime.strptime(checkout, '%Y-%m-%d').date()
    except (TypeError, ValueError):
        return None, None, error_response('Formato de data invalido. Use YYYY-MM-DD.', 'DATAS_INVALIDAS', 400)

    if checkout_date <= checkin_date:
        return None, None, error_response('Checkout deve ser posterior ao checkin.', 'DATAS_INVALIDAS', 400)

    return checkin_date, checkout_date, None


def _parse_quarto_id(data):
    quartos_payload = data.get('quartos') or []
    try:
        return int(quartos_payload[0]), None
    except (IndexError, TypeError, ValueError):
        return None, error_response('Selecione um quarto valido.', 'QUARTO_INDISPONIVEL', 400)


def _parse_acompanhantes(data):
    try:
        return [int(acompanhante_id) for acompanhante_id in data.get('acompanhantes', []) if acompanhante_id], None
    except (TypeError, ValueError):
        return None, error_response('Lista de acompanhantes invalida.', 'VALIDATION_ERROR', 400)


def _validar_operacao_reserva(cursor, data, acompanhante_ids, reserva_id_atual=None):
    barco_id, error = _parse_required_int(
        data,
        'fk_barco',
        'Selecione um barco para a reserva.',
        'BARCO_OBRIGATORIO',
    )
    if error:
        return None, error

    tipo_passeio_id, error = _parse_required_int(
        data,
        'fk_tipo_passeio',
        'Selecione o tipo de passeio da reserva.',
        'TIPO_PASSEIO_OBRIGATORIO',
    )
    if error:
        return None, error

    data_embarque, error = _parse_required_date(data, 'data_embarque', 'Data de embarque e obrigatoria.')
    if error:
        return None, error

    data_desembarque, error = _parse_required_date(data, 'data_desembarque', 'Data de desembarque e obrigatoria.')
    if error:
        return None, error

    if data_desembarque < data_embarque:
        return None, error_response(
            'Data de desembarque deve ser igual ou posterior ao embarque.',
            'DATAS_OPERACAO_INVALIDAS',
            400,
        )

    barco = reserva_repository.bloquear_barco(cursor, barco_id)
    if not barco:
        return None, error_response('Barco nao encontrado.', 'BARCO_NOT_FOUND', 404)

    if barco['status_barco'] != 'Disponível':
        return None, error_response(
            'Este barco nao esta disponivel para reserva.',
            'BARCO_INDISPONIVEL',
            409,
            {
                'nome_barco': barco['nome_barco'],
                'status_barco': barco['status_barco'],
            },
        )

    total_pessoas = 1 + len(acompanhante_ids)
    if total_pessoas > barco['capacidade_pessoas']:
        return None, error_response(
            'A quantidade de pessoas excede a capacidade do barco.',
            'CAPACIDADE_BARCO_EXCEDIDA',
            409,
            {
                'nome_barco': barco['nome_barco'],
                'capacidade_pessoas': barco['capacidade_pessoas'],
                'total_pessoas': total_pessoas,
            },
        )

    tipo_passeio = reserva_repository.buscar_tipo_passeio_ativo(cursor, tipo_passeio_id)
    if not tipo_passeio:
        return None, error_response('Tipo de passeio nao encontrado ou inativo.', 'TIPO_PASSEIO_INVALIDO', 404)

    conflito_barco = reserva_repository.buscar_conflito_barco(
        cursor,
        barco_id,
        data_embarque,
        data_desembarque,
        reserva_id_atual=reserva_id_atual,
    )
    if conflito_barco:
        return None, error_response(
            'Este barco ja esta reservado no periodo da viagem.',
            'BARCO_OVERBOOK',
            409,
            conflito_barco,
        )

    return {
        'fk_barco': barco_id,
        'fk_tipo_passeio': tipo_passeio_id,
        'data_embarque': data_embarque,
        'data_desembarque': data_desembarque,
        'local_embarque': data.get('local_embarque') or None,
        'local_desembarque': data.get('local_desembarque') or None,
        'observacao_operacional': data.get('observacao_operacional') or None,
        'nome_barco': barco['nome_barco'],
        'tipo_passeio': tipo_passeio['nome_tipo'],
    }, None


@transaction.atomic
def criar_reserva(request):
    data, parse_error = _parse_json_body(request)
    if parse_error:
        return parse_error

    titular_id, error = _parse_required_int(
        data,
        'fk_hospede_id_hospede',
        'Selecione um titular valido para a reserva.',
        'TITULAR_OBRIGATORIO',
    )
    if error:
        return error

    quarto_id, error = _parse_quarto_id(data)
    if error:
        return error

    checkin_date, checkout_date, error = _parse_data_estadia(data)
    if error:
        return error

    acompanhante_ids, error = _parse_acompanhantes(data)
    if error:
        return error

    status_pagamento = data.get('status_pagamento') or 'Pendente'
    usuario_id = request.user_token_payload.get('id_usuario')

    try:
        with connection.cursor() as cursor:
            quarto = reserva_repository.bloquear_quarto(cursor, quarto_id)
            if not quarto:
                return error_response('Quarto nao encontrado.', 'NOT_FOUND', 404)

            if quarto['status_quarto'] == 'Manutenção':
                return error_response('Quarto em manutencao nao pode ser reservado.', 'QUARTO_MANUTENCAO', 409)

            operacao_reserva, operacao_error = _validar_operacao_reserva(cursor, data, acompanhante_ids)
            if operacao_error:
                return operacao_error

            conflito_quarto = reserva_repository.buscar_conflito_quarto(
                cursor,
                quarto_id,
                checkin_date,
                checkout_date,
            )
            if conflito_quarto:
                return error_response(
                    'Este quarto ja esta ocupado no periodo solicitado.',
                    'OVERBOOK',
                    409,
                    conflito_quarto,
                )

            diarias = (checkout_date - checkin_date).days
            valor_total = quarto['valor_diaria'] * diarias

            reserva_id = reserva_repository.criar_reserva(
                cursor,
                {
                    'valor_total': valor_total,
                    'observacao_reserva': data.get('observacao_reserva'),
                    'usuario_id': usuario_id,
                    'status_pagamento': status_pagamento,
                    'titular_id': titular_id,
                    **operacao_reserva,
                },
            )
            reserva_quarto_id = reserva_repository.criar_reserva_quarto(
                cursor,
                reserva_id,
                quarto_id,
                checkin_date,
                checkout_date,
                quarto['valor_diaria'],
            )
            reserva_repository.inserir_acompanhantes(cursor, reserva_id, acompanhante_ids)

            nome_titular = reserva_repository.buscar_nome_hospede(cursor, titular_id)

        nova_reserva = {
            'id_reserva_quarto': reserva_quarto_id,
            'checkin': checkin_date,
            'checkout': checkout_date,
            'id_reserva': reserva_id,
            'status_reserva': 'Agendada',
            'status_pagamento': status_pagamento,
            'id_quarto': quarto_id,
            'numero_quarto': quarto['numero'],
            'nome_titular': nome_titular,
            'valor_total': float(valor_total),
            'fk_barco': operacao_reserva['fk_barco'],
            'nome_barco': operacao_reserva['nome_barco'],
            'fk_tipo_passeio': operacao_reserva['fk_tipo_passeio'],
            'tipo_passeio': operacao_reserva['tipo_passeio'],
            'data_embarque': operacao_reserva['data_embarque'],
            'data_desembarque': operacao_reserva['data_desembarque'],
            'local_embarque': operacao_reserva['local_embarque'],
            'local_desembarque': operacao_reserva['local_desembarque'],
            'status_operacional': 'A Preparar',
            'observacao_operacional': operacao_reserva['observacao_operacional'],
        }

        return success_response(nova_reserva, status_code=201)
    except IntegrityError as exc:
        return error_response(f'Erro de integridade no banco: {str(exc)}', 'DB_INTEGRITY_ERROR', 400)
    except Exception as exc:
        return error_response(str(exc), 'ERRO_INTERNO', 500)


@transaction.atomic
def editar_reserva(request, reserva_quarto_id):
    data, parse_error = _parse_json_body(request)
    if parse_error:
        return parse_error

    titular_id, error = _parse_required_int(
        data,
        'fk_hospede_id_hospede',
        'Selecione um titular valido para a reserva.',
        'TITULAR_OBRIGATORIO',
    )
    if error:
        return error

    quarto_id, error = _parse_quarto_id(data)
    if error:
        return error

    checkin_date, checkout_date, error = _parse_data_estadia(data)
    if error:
        return error

    acompanhante_ids, error = _parse_acompanhantes(data)
    if error:
        return error

    status_pagamento = data.get('status_pagamento') or 'Pendente'
    usuario_id = request.user_token_payload.get('id_usuario')

    try:
        with connection.cursor() as cursor:
            reserva_data = reserva_repository.buscar_reserva_quarto_para_edicao(cursor, reserva_quarto_id)
            if not reserva_data:
                return error_response('Reserva (link quarto) nao encontrada.', 'NOT_FOUND', 404)

            reserva_id = reserva_data['fk_reserva']
            status_reserva_atual = reserva_data['status_reserva']

            if status_reserva_atual in ('Ativa', 'Concluída'):
                if reserva_data['checkin'] != checkin_date or reserva_data['checkout'] != checkout_date:
                    return error_response(
                        'Reservas ativas ou concluidas nao podem ter datas alteradas.',
                        'OPERACAO_NAO_PERMITIDA',
                        409,
                    )

            quarto = reserva_repository.bloquear_quarto(cursor, quarto_id)
            if not quarto:
                return error_response('Quarto nao encontrado.', 'NOT_FOUND', 404)

            if quarto['status_quarto'] == 'Manutenção':
                return error_response('Quarto em manutencao nao pode ser reservado.', 'QUARTO_MANUTENCAO', 409)

            operacao_reserva, operacao_error = _validar_operacao_reserva(
                cursor,
                data,
                acompanhante_ids,
                reserva_id_atual=reserva_id,
            )
            if operacao_error:
                return operacao_error

            conflito_quarto = reserva_repository.buscar_conflito_quarto(
                cursor,
                quarto_id,
                checkin_date,
                checkout_date,
                reserva_quarto_id=reserva_quarto_id,
            )
            if conflito_quarto:
                return error_response(
                    'Este quarto ja esta ocupado no periodo solicitado por outra reserva.',
                    'OVERBOOK',
                    409,
                    conflito_quarto,
                )

            diarias = (checkout_date - checkin_date).days
            valor_total = quarto['valor_diaria'] * diarias

            reserva_repository.atualizar_reserva_principal(
                cursor,
                reserva_id,
                {
                    'valor_total': valor_total,
                    'observacao_reserva': data.get('observacao_reserva'),
                    'usuario_id': usuario_id,
                    'status_pagamento': status_pagamento,
                    'titular_id': titular_id,
                    **operacao_reserva,
                },
            )
            reserva_repository.atualizar_reserva_quarto(
                cursor,
                reserva_quarto_id,
                quarto_id,
                checkin_date,
                checkout_date,
                quarto['valor_diaria'],
            )
            reserva_repository.substituir_acompanhantes(cursor, reserva_id, acompanhante_ids)

            reserva_obj = reserva_repository.buscar_reserva_detalhes(reserva_quarto_id, cursor=cursor)
            if not reserva_obj:
                return error_response('Reserva nao encontrada apos atualizacao.', 'NOT_FOUND', 404)

        return success_response(reserva_obj)
    except IntegrityError as exc:
        return error_response(f'Erro de integridade no banco: {str(exc)}', 'DB_INTEGRITY_ERROR', 400)
    except Exception as exc:
        return error_response(str(exc), 'ERRO_INTERNO', 500)


@transaction.atomic
def atualizar_status(request, reserva_quarto_id):
    try:
        data = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return error_response('JSON invalido.', 'INVALID_JSON', 400)

    novo_status_reserva = data.get('status_reserva')
    novo_status_pagamento = data.get('status_pagamento')
    novo_status_operacional = data.get('status_operacional')

    if not novo_status_reserva and not novo_status_pagamento and not novo_status_operacional:
        return error_response('Nenhum status foi enviado para atualização.', 'VALIDATION_ERROR', 400)

    if novo_status_operacional and novo_status_operacional not in STATUS_OPERACIONAL_VALIDOS:
        return error_response('Status operacional invalido.', 'VALIDATION_ERROR', 400)

    with connection.cursor() as cursor:
        reserva_id = reserva_repository.buscar_reserva_id_por_reserva_quarto(cursor, reserva_quarto_id)
        if not reserva_id:
            return error_response('Reserva (link quarto) não encontrada.', 'NOT_FOUND', 404)

        if not reserva_repository.bloquear_reserva(cursor, reserva_id):
            return error_response('Reserva não encontrada.', 'NOT_FOUND', 404)

        campos = {}
        if novo_status_reserva:
            campos['status_reserva'] = novo_status_reserva
        if novo_status_pagamento:
            campos['status_pagamento'] = novo_status_pagamento
        if novo_status_operacional:
            campos['status_operacional'] = novo_status_operacional

        reserva_repository.atualizar_status_reserva(cursor, reserva_id, campos)
        reserva_obj = reserva_repository.buscar_reserva_detalhes(reserva_quarto_id, cursor=cursor)

    if not reserva_obj:
        return error_response('Reserva não encontrada após atualização.', 'NOT_FOUND', 404)

    return success_response(reserva_obj)
