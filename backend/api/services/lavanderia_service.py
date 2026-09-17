import json
from decimal import Decimal
from json import JSONDecodeError

from django.db import connection, transaction

from ..repositories import consumo_repository
from ..repositories import lavanderia_repository
from ..responses import error_response, success_response


STATUS_ATIVO_VALIDOS = ('Ativo', 'Inativo')
STATUS_LAVANDERIA_VALIDOS = ('Recebido', 'Em Lavagem', 'Pronto', 'Entregue', 'Cancelado')


def listar_categorias(request):
    ativo = request.GET.get('ativo') or 'Ativo'
    if ativo != 'Todos' and ativo not in STATUS_ATIVO_VALIDOS:
        return None, error_response('Status da categoria invalido.', 'VALIDATION_ERROR', 400)

    return lavanderia_repository.buscar_categorias(ativo), None


def listar_servicos(request):
    ativo = request.GET.get('ativo') or 'Ativo'
    if ativo != 'Todos' and ativo not in STATUS_ATIVO_VALIDOS:
        return None, error_response('Status do servico invalido.', 'VALIDATION_ERROR', 400)

    categoria_id = request.GET.get('fk_categoria') or request.GET.get('id_categoria')
    if categoria_id:
        try:
            categoria_id = int(categoria_id)
        except (TypeError, ValueError):
            return None, error_response('Categoria deve ser um numero inteiro.', 'VALIDATION_ERROR', 400)
        if categoria_id < 1:
            return None, error_response('Categoria deve ser maior ou igual a 1.', 'VALIDATION_ERROR', 400)

    return lavanderia_repository.buscar_servicos(ativo, categoria_id), None


def _parse_json_body(request):
    try:
        if not request.body:
            return {}, None
        return json.loads(request.body), None
    except JSONDecodeError:
        return None, error_response('JSON invalido.', 'INVALID_JSON', 400)


def _parse_int(value, field_label, minimum=None):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None, error_response(f'{field_label} deve ser um numero inteiro.', 'VALIDATION_ERROR', 400)

    if minimum is not None and parsed < minimum:
        return None, error_response(f'{field_label} deve ser maior ou igual a {minimum}.', 'VALIDATION_ERROR', 400)

    return parsed, None


def _normalizar_observacao(observacao):
    if isinstance(observacao, str) and observacao.strip():
        return observacao.strip()
    return None


def _listar_ordens(request):
    status = request.GET.get('status')
    conta_id = request.GET.get('fk_conta') or request.GET.get('id_conta')
    reserva_id = request.GET.get('fk_reserva') or request.GET.get('id_reserva')

    if status and status not in STATUS_LAVANDERIA_VALIDOS:
        return None, error_response('Status de lavanderia invalido.', 'VALIDATION_ERROR', 400)

    if conta_id:
        conta_id, error = _parse_int(conta_id, 'Conta', 1)
        if error:
            return None, error

    if reserva_id:
        reserva_id, error = _parse_int(reserva_id, 'Reserva', 1)
        if error:
            return None, error

    ordens = lavanderia_repository.buscar_ordens(
        status=status,
        conta_id=conta_id,
        reserva_id=reserva_id,
    )
    return ordens, None


def _validar_item_ordem(item, cursor):
    servico_id = item.get('fk_servico') or item.get('id_servico')
    servico_id, error = _parse_int(servico_id, 'Servico', 1)
    if error:
        return None, error

    quantidade, error = _parse_int(item.get('quantidade'), 'Quantidade', 1)
    if error:
        return None, error

    servico = lavanderia_repository.buscar_servico_para_ordem(cursor, servico_id)
    if not servico:
        return None, error_response('Servico de lavanderia nao encontrado ou inativo.', 'SERVICO_INATIVO', 404)

    valor_unitario = servico['preco_unitario']
    subtotal = valor_unitario * quantidade
    return {
        'id_servico': servico_id,
        'nome_servico': servico['nome_servico'],
        'nome_categoria': servico['nome_categoria'],
        'prazo_horas': int(servico['prazo_horas'] or 24),
        'quantidade': quantidade,
        'valor_unitario': valor_unitario,
        'subtotal': subtotal,
        'observacao': item.get('observacao'),
    }, None


@transaction.atomic
def listar_ou_criar_ordens(request):
    if request.method == 'GET':
        try:
            ordens, error = _listar_ordens(request)
            if error:
                return error
            return success_response(ordens)
        except Exception as exc:
            return error_response(str(exc), 'SERVER_ERROR', 500)

    data, parse_error = _parse_json_body(request)
    if parse_error:
        return parse_error

    reserva_id = data.get('fk_reserva') or data.get('id_reserva')
    reserva_id, error = _parse_int(reserva_id, 'Reserva', 1)
    if error:
        return error

    itens = data.get('itens') or []
    if not isinstance(itens, list) or not itens:
        return error_response('Informe ao menos uma peca para a lavanderia.', 'VALIDATION_ERROR', 400)

    usuario_id = request.user_token_payload.get('id_usuario')
    observacao = _normalizar_observacao(data.get('observacao'))

    try:
        with connection.cursor() as cursor:
            reserva = consumo_repository.buscar_reserva_para_consumo(cursor, reserva_id)
            if not reserva:
                return error_response('Reserva nao encontrada.', 'NOT_FOUND', 404)
            if reserva['status_reserva'] != 'Ativa':
                return error_response('Apenas reservas ativas podem receber lavanderia.', 'RESERVA_INATIVA', 409)

            conta = consumo_repository.buscar_ou_criar_conta_consumo(cursor, reserva_id)
            if conta['status_conta'] != 'Aberta':
                return error_response('A conta de consumo desta reserva nao esta aberta.', 'CONTA_FECHADA', 409)

            itens_processados = []
            total_ordem = Decimal('0.00')
            maior_prazo = 24

            for item in itens:
                item_processado, item_error = _validar_item_ordem(item, cursor)
                if item_error:
                    return item_error
                total_ordem += item_processado['subtotal']
                maior_prazo = max(maior_prazo, item_processado['prazo_horas'])
                itens_processados.append(item_processado)

            ordem = lavanderia_repository.criar_ordem(
                cursor,
                conta['id_conta'],
                reserva_id,
                usuario_id,
                observacao,
                total_ordem,
                maior_prazo,
            )

            itens_response = []
            for item in itens_processados:
                item_salvo = lavanderia_repository.criar_item_ordem(cursor, ordem['id_ordem'], item)
                item_salvo['nome_servico'] = item['nome_servico']
                item_salvo['nome_categoria'] = item['nome_categoria']
                itens_response.append(item_salvo)

            lavanderia_repository.registrar_historico_status(
                cursor,
                ordem['id_ordem'],
                None,
                'Recebido',
                usuario_id,
                'Ordem criada pelo app mobile',
            )

            conta_atualizada = consumo_repository.incrementar_total_conta(
                cursor,
                conta['id_conta'],
                total_ordem,
            )

        ordem['itens'] = itens_response
        ordem['total_acumulado_conta'] = conta_atualizada['total_acumulado']
        return success_response(ordem, 'ORDEM_LAVANDERIA_CREATED', 201)
    except Exception as exc:
        return error_response(str(exc), 'SERVER_ERROR', 500)


@transaction.atomic
def atualizar_status(request, ordem_id):
    data, parse_error = _parse_json_body(request)
    if parse_error:
        return parse_error

    novo_status = data.get('status_ordem') or data.get('status')
    if novo_status not in STATUS_LAVANDERIA_VALIDOS:
        return error_response('Status de lavanderia invalido.', 'VALIDATION_ERROR', 400)

    observacao = _normalizar_observacao(data.get('observacao'))
    usuario_id = request.user_token_payload.get('id_usuario')

    try:
        with connection.cursor() as cursor:
            ordem_atual = lavanderia_repository.buscar_ordem_para_status(cursor, ordem_id)
            if not ordem_atual:
                return error_response('Ordem de lavanderia nao encontrada.', 'NOT_FOUND', 404)

            status_anterior = ordem_atual['status_ordem']
            if status_anterior == novo_status:
                return success_response(ordem_atual, 'ORDEM_LAVANDERIA_STATUS_UNCHANGED')

            ordem = lavanderia_repository.atualizar_status_ordem(cursor, ordem_id, novo_status)

            if novo_status == 'Cancelado' and status_anterior != 'Cancelado':
                lavanderia_repository.abater_total_conta(
                    cursor,
                    ordem_atual['fk_conta'],
                    ordem_atual['total_ordem'],
                )

            lavanderia_repository.registrar_historico_status(
                cursor,
                ordem_id,
                status_anterior,
                novo_status,
                usuario_id,
                observacao,
            )

        return success_response(ordem, 'ORDEM_LAVANDERIA_STATUS_UPDATED')
    except Exception as exc:
        return error_response(str(exc), 'SERVER_ERROR', 500)
