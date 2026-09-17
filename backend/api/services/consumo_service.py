import json
from decimal import Decimal
from json import JSONDecodeError

from django.db import connection, transaction

from ..repositories import consumo_repository
from ..responses import error_response, success_response

TIPOS_CONSUMO_VALIDOS = ('Restaurante', 'Lojinha', 'Outros')
CATEGORIA_BEBIDAS_CONSUMO = 'Bebidas'


def buscar_reservas_abertas():
    return consumo_repository.buscar_reservas_abertas()


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


def _is_categoria_bebidas(nome_categoria):
    return (nome_categoria or '').strip().lower() == CATEGORIA_BEBIDAS_CONSUMO.lower()


def _validar_categoria_open_food(tipo_categoria, nome_categoria):
    if tipo_categoria == 'Restaurante' and not _is_categoria_bebidas(nome_categoria):
        return error_response(
            'No pacote open food, a origem Bebidas aceita apenas a categoria Bebidas.',
            'CATEGORIA_OPEN_FOOD_INVALIDA',
            400,
        )
    return None


def _normalizar_observacao(observacao):
    if isinstance(observacao, str) and observacao.strip():
        return observacao.strip()
    return None


def _validar_item_venda(item, origem, cursor):
    produto_id = item.get('fk_produto') or item.get('id_produto')
    produto_id, error = _parse_int(produto_id, 'Produto', 1)
    if error:
        return None, error

    quantidade, error = _parse_int(item.get('quantidade'), 'Quantidade', 1)
    if error:
        return None, error

    produto = consumo_repository.buscar_produto_para_venda(cursor, produto_id)
    if not produto:
        return None, error_response('Produto nao encontrado ou inativo.', 'PRODUTO_INATIVO', 404)

    if produto['tipo_categoria'] != origem:
        return None, error_response(
            'Produto nao pertence a origem informada para a venda.',
            'PRODUTO_ORIGEM_INVALIDA',
            400,
            {
                'id_produto': produto_id,
                'origem_venda': origem,
                'origem_produto': produto['tipo_categoria'],
            },
        )

    open_food_error = _validar_categoria_open_food(produto['tipo_categoria'], produto['nome_categoria'])
    if open_food_error:
        return None, open_food_error

    if produto['controla_estoque'] and produto['estoque_atual'] < quantidade:
        return None, error_response(
            'Estoque insuficiente para o produto.',
            'ESTOQUE_INSUFICIENTE',
            409,
            {
                'id_produto': produto_id,
                'nome_produto': produto['nome_produto'],
                'estoque_atual': produto['estoque_atual'],
                'quantidade_solicitada': quantidade,
            },
        )

    valor_unitario = produto['preco_atual']
    subtotal = valor_unitario * quantidade
    return {
        'id_produto': produto_id,
        'nome_produto': produto['nome_produto'],
        'quantidade': quantidade,
        'valor_unitario': valor_unitario,
        'subtotal': subtotal,
        'observacao': item.get('observacao'),
        'controla_estoque': produto['controla_estoque'],
        'estoque_atual': produto['estoque_atual'],
    }, None


@transaction.atomic
def criar_venda(request):
    data, parse_error = _parse_json_body(request)
    if parse_error:
        return parse_error

    reserva_id = data.get('fk_reserva') or data.get('id_reserva')
    reserva_id, error = _parse_int(reserva_id, 'Reserva', 1)
    if error:
        return error

    origem = data.get('origem') or data.get('tipo_categoria') or 'Restaurante'
    if origem not in TIPOS_CONSUMO_VALIDOS:
        return error_response('Origem de consumo invalida.', 'VALIDATION_ERROR', 400)

    itens = data.get('itens') or []
    if not isinstance(itens, list) or not itens:
        return error_response('Informe ao menos um item para a venda.', 'VALIDATION_ERROR', 400)

    usuario_id = request.user_token_payload.get('id_usuario')
    observacao = _normalizar_observacao(data.get('observacao'))

    try:
        with connection.cursor() as cursor:
            reserva = consumo_repository.buscar_reserva_para_consumo(cursor, reserva_id)
            if not reserva:
                return error_response('Reserva nao encontrada.', 'NOT_FOUND', 404)
            if reserva['status_reserva'] != 'Ativa':
                return error_response('Apenas reservas ativas podem receber consumo.', 'RESERVA_INATIVA', 409)

            conta = consumo_repository.buscar_ou_criar_conta_consumo(cursor, reserva_id)
            if conta['status_conta'] != 'Aberta':
                return error_response('A conta de consumo desta reserva nao esta aberta.', 'CONTA_FECHADA', 409)

            itens_processados = []
            total_venda = Decimal('0.00')

            for item in itens:
                item_processado, item_error = _validar_item_venda(item, origem, cursor)
                if item_error:
                    return item_error
                total_venda += item_processado['subtotal']
                itens_processados.append(item_processado)

            venda = consumo_repository.criar_venda(
                cursor,
                conta['id_conta'],
                reserva_id,
                usuario_id,
                origem,
                observacao,
                total_venda,
            )

            itens_response = []
            for item in itens_processados:
                item_salvo = consumo_repository.criar_item_venda(cursor, venda['id_venda'], item)
                item_salvo['nome_produto'] = item['nome_produto']
                itens_response.append(item_salvo)

                if item['controla_estoque']:
                    estoque_anterior = item['estoque_atual']
                    estoque_posterior = estoque_anterior - item['quantidade']
                    consumo_repository.atualizar_estoque_produto(
                        cursor,
                        item['id_produto'],
                        estoque_posterior,
                    )
                    consumo_repository.registrar_movimento_estoque(
                        cursor,
                        item['id_produto'],
                        usuario_id,
                        item_salvo['id_item'],
                        item['quantidade'],
                        estoque_anterior,
                        estoque_posterior,
                        f'Venda consumo #{venda["id_venda"]}',
                    )

            conta_atualizada = consumo_repository.incrementar_total_conta(
                cursor,
                conta['id_conta'],
                total_venda,
            )

        venda['itens'] = itens_response
        venda['total_acumulado_conta'] = conta_atualizada['total_acumulado']
        return success_response(venda, 'VENDA_CREATED', 201)
    except Exception as exc:
        return error_response(str(exc), 'SERVER_ERROR', 500)


def buscar_conta_detalhe(conta_id):
    return consumo_repository.buscar_conta_detalhe(conta_id)


@transaction.atomic
def fechar_conta(conta_id):
    conta = consumo_repository.fechar_conta(conta_id)
    if not conta:
        return error_response('Conta nao encontrada ou ja fechada.', 'CONTA_NAO_ABERTA', 409)

    return success_response(conta, 'CONTA_FECHADA')
