import json
from decimal import Decimal, InvalidOperation

from django.db import IntegrityError
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from ..access_control import CONSUMO_LAVANDERIA_ROLES, FULL_ACCESS_ROLES
from ..auth_decorator import token_required
from ..models import CategoriaProduto, Produto
from ..responses import error_response, success_response


TIPOS_CONSUMO_VALIDOS = ('Restaurante', 'Lojinha', 'Outros')
STATUS_ATIVO_VALIDOS = ('Ativo', 'Inativo')
CATEGORIA_BEBIDAS_CONSUMO = 'Bebidas'


def _parse_json_body(request):
    try:
        if not request.body:
            return {}, None
        return json.loads(request.body), None
    except json.JSONDecodeError:
        return None, error_response('JSON invalido.', 'INVALID_JSON', 400)


def _parse_bool(value, default=False):
    if value in (None, ''):
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in ('true', '1', 'sim', 'yes'):
            return True
        if normalized in ('false', '0', 'nao', 'n\u00e3o', 'no'):
            return False
    return bool(value)


def _parse_decimal(value, field_label, allow_zero=True):
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None, error_response(f'{field_label} deve ser um numero valido.', 'VALIDATION_ERROR', 400)

    if parsed < 0 or (not allow_zero and parsed == 0):
        return None, error_response(f'{field_label} deve ser maior que zero.', 'VALIDATION_ERROR', 400)

    return parsed, None


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


def _validar_categoria_consumo_payload(data):
    nome_categoria = (data.get('nome_categoria') or '').strip()
    tipo_categoria = data.get('tipo_categoria') or data.get('origem') or 'Restaurante'
    ativo = data.get('ativo') or 'Ativo'

    if not nome_categoria:
        return None, error_response('Nome da categoria e obrigatorio.', 'VALIDATION_ERROR', 400)

    if tipo_categoria not in TIPOS_CONSUMO_VALIDOS:
        return None, error_response('Tipo de categoria invalido.', 'VALIDATION_ERROR', 400)

    if ativo not in STATUS_ATIVO_VALIDOS:
        return None, error_response('Status da categoria invalido.', 'VALIDATION_ERROR', 400)

    open_food_error = _validar_categoria_open_food(tipo_categoria, nome_categoria)
    if open_food_error:
        return None, open_food_error

    return {
        'nome_categoria': nome_categoria,
        'tipo_categoria': tipo_categoria,
        'ativo': ativo,
    }, None


def _validar_produto_consumo_payload(data):
    nome_produto = (data.get('nome_produto') or '').strip()
    if not nome_produto:
        return None, error_response('Nome do produto e obrigatorio.', 'VALIDATION_ERROR', 400)

    categoria_id, error = _parse_int(data.get('fk_categoria'), 'Categoria', 1)
    if error:
        return None, error

    preco_atual, error = _parse_decimal(data.get('preco_atual'), 'Preco atual')
    if error:
        return None, error

    controla_estoque = _parse_bool(data.get('controla_estoque'), False)
    estoque_atual, error = _parse_int(data.get('estoque_atual') or 0, 'Estoque atual', 0)
    if error:
        return None, error

    estoque_minimo, error = _parse_int(data.get('estoque_minimo') or 0, 'Estoque minimo', 0)
    if error:
        return None, error

    ativo = data.get('ativo') or 'Ativo'
    if ativo not in STATUS_ATIVO_VALIDOS:
        return None, error_response('Status do produto invalido.', 'VALIDATION_ERROR', 400)

    if not controla_estoque:
        estoque_atual = 0
        estoque_minimo = 0

    descricao = data.get('descricao')

    return {
        'categoria_id': categoria_id,
        'nome_produto': nome_produto,
        'descricao': descricao.strip() if isinstance(descricao, str) and descricao.strip() else None,
        'preco_atual': preco_atual,
        'controla_estoque': controla_estoque,
        'estoque_atual': estoque_atual,
        'estoque_minimo': estoque_minimo,
        'ativo': ativo,
    }, None


def _categoria_to_dict(categoria):
    return {
        'id_categoria': categoria.id_categoria,
        'nome_categoria': categoria.nome_categoria,
        'tipo_categoria': categoria.tipo_categoria,
        'ativo': categoria.ativo,
        'dt_criacao': categoria.dt_criacao,
    }


def _produto_to_dict(produto):
    return {
        'id_produto': produto.id_produto,
        'fk_categoria': produto.categoria_id,
        'nome_categoria': produto.categoria.nome_categoria,
        'tipo_categoria': produto.categoria.tipo_categoria,
        'nome_produto': produto.nome_produto,
        'descricao': produto.descricao,
        'preco_atual': float(produto.preco_atual),
        'controla_estoque': produto.controla_estoque,
        'estoque_atual': produto.estoque_atual,
        'estoque_minimo': produto.estoque_minimo,
        'ativo': produto.ativo,
        'dt_criacao': produto.dt_criacao,
        'dt_atualizacao': produto.dt_atualizacao,
    }


def _buscar_categoria_ativa_para_produto(categoria_id):
    try:
        categoria = CategoriaProduto.objects.get(pk=categoria_id)
    except CategoriaProduto.DoesNotExist:
        return None, error_response('Categoria nao encontrada.', 'NOT_FOUND', 404)

    if categoria.ativo != 'Ativo':
        return None, error_response('Categoria inativa para cadastro de produto.', 'CATEGORIA_INATIVA', 400)

    open_food_error = _validar_categoria_open_food(
        categoria.tipo_categoria,
        categoria.nome_categoria,
    )
    if open_food_error:
        return None, open_food_error

    return categoria, None


@csrf_exempt
@token_required(method_roles={'GET': CONSUMO_LAVANDERIA_ROLES, 'POST': FULL_ACCESS_ROLES})
@require_http_methods(["GET", "POST"])
def consumo_categorias_view(request):
    if request.method == 'POST':
        data, parse_error = _parse_json_body(request)
        if parse_error:
            return parse_error

        payload, error = _validar_categoria_consumo_payload(data)
        if error:
            return error

        try:
            categoria = CategoriaProduto.objects.create(**payload)
            return success_response(_categoria_to_dict(categoria), 'CATEGORIA_CREATED', 201)
        except IntegrityError:
            return error_response('Categoria ja cadastrada para este tipo.', 'CONFLICT', 409)
        except Exception as exc:
            return error_response(str(exc), 'SERVER_ERROR', 500)

    tipo_categoria = request.GET.get('tipo_categoria') or request.GET.get('origem')
    ativo = request.GET.get('ativo') or 'Ativo'

    try:
        categorias = CategoriaProduto.objects.all().order_by('tipo_categoria', 'nome_categoria')

        if tipo_categoria:
            if tipo_categoria not in TIPOS_CONSUMO_VALIDOS:
                return error_response('Tipo de categoria invalido.', 'VALIDATION_ERROR', 400)
            categorias = categorias.filter(tipo_categoria=tipo_categoria)

        if ativo != 'Todos':
            if ativo not in STATUS_ATIVO_VALIDOS:
                return error_response('Status da categoria invalido.', 'VALIDATION_ERROR', 400)
            categorias = categorias.filter(ativo=ativo)

        return success_response([_categoria_to_dict(categoria) for categoria in categorias])
    except Exception as exc:
        return error_response(str(exc), 'SERVER_ERROR', 500)


@csrf_exempt
@token_required(method_roles={'GET': CONSUMO_LAVANDERIA_ROLES, 'POST': FULL_ACCESS_ROLES})
@require_http_methods(["GET", "POST"])
def consumo_produtos_view(request):
    if request.method == 'POST':
        data, parse_error = _parse_json_body(request)
        if parse_error:
            return parse_error

        payload, error = _validar_produto_consumo_payload(data)
        if error:
            return error

        categoria, error = _buscar_categoria_ativa_para_produto(payload.pop('categoria_id'))
        if error:
            return error

        try:
            produto = Produto.objects.create(categoria=categoria, **payload)
            produto = Produto.objects.select_related('categoria').get(pk=produto.pk)
            return success_response(_produto_to_dict(produto), 'PRODUTO_CREATED', 201)
        except IntegrityError:
            return error_response('Produto ja cadastrado nesta categoria.', 'CONFLICT', 409)
        except Exception as exc:
            return error_response(str(exc), 'SERVER_ERROR', 500)

    origem = request.GET.get('origem') or request.GET.get('tipo_categoria')
    ativo = request.GET.get('ativo') or 'Ativo'

    try:
        produtos = Produto.objects.select_related('categoria').order_by(
            'categoria__tipo_categoria',
            'categoria__nome_categoria',
            'nome_produto',
        )

        if origem:
            if origem not in TIPOS_CONSUMO_VALIDOS:
                return error_response('Origem de consumo invalida.', 'VALIDATION_ERROR', 400)
            produtos = produtos.filter(categoria__tipo_categoria=origem)

        if ativo != 'Todos':
            if ativo not in STATUS_ATIVO_VALIDOS:
                return error_response('Status do produto invalido.', 'VALIDATION_ERROR', 400)
            produtos = produtos.filter(ativo=ativo)

        return success_response([_produto_to_dict(produto) for produto in produtos])
    except Exception as exc:
        return error_response(str(exc), 'SERVER_ERROR', 500)


@csrf_exempt
@token_required(method_roles={'GET': CONSUMO_LAVANDERIA_ROLES, 'PUT': FULL_ACCESS_ROLES, 'PATCH': FULL_ACCESS_ROLES})
@require_http_methods(["GET", "PUT", "PATCH"])
def consumo_produto_detail_view(request, produto_id):
    if request.method == 'GET':
        try:
            produto = Produto.objects.select_related('categoria').get(pk=produto_id)
            return success_response(_produto_to_dict(produto))
        except Produto.DoesNotExist:
            return error_response('Produto nao encontrado.', 'NOT_FOUND', 404)
        except Exception as exc:
            return error_response(str(exc), 'SERVER_ERROR', 500)

    data, parse_error = _parse_json_body(request)
    if parse_error:
        return parse_error

    if request.method == 'PATCH':
        ativo = data.get('ativo')
        if ativo not in STATUS_ATIVO_VALIDOS:
            return error_response('Status do produto invalido.', 'VALIDATION_ERROR', 400)

        try:
            produto = Produto.objects.get(pk=produto_id)
            produto.ativo = ativo
            produto.dt_atualizacao = timezone.now()
            produto.save(update_fields=['ativo', 'dt_atualizacao'])
            return success_response(
                {
                    'id_produto': produto.id_produto,
                    'ativo': produto.ativo,
                    'dt_atualizacao': produto.dt_atualizacao,
                },
                'PRODUTO_STATUS_UPDATED',
            )
        except Produto.DoesNotExist:
            return error_response('Produto nao encontrado.', 'NOT_FOUND', 404)
        except Exception as exc:
            return error_response(str(exc), 'SERVER_ERROR', 500)

    payload, error = _validar_produto_consumo_payload(data)
    if error:
        return error

    categoria, error = _buscar_categoria_ativa_para_produto(payload.pop('categoria_id'))
    if error:
        return error

    try:
        produto = Produto.objects.get(pk=produto_id)
        produto.categoria = categoria
        produto.nome_produto = payload['nome_produto']
        produto.descricao = payload['descricao']
        produto.preco_atual = payload['preco_atual']
        produto.controla_estoque = payload['controla_estoque']
        produto.estoque_atual = payload['estoque_atual']
        produto.estoque_minimo = payload['estoque_minimo']
        produto.ativo = payload['ativo']
        produto.dt_atualizacao = timezone.now()
        produto.save(
            update_fields=[
                'categoria',
                'nome_produto',
                'descricao',
                'preco_atual',
                'controla_estoque',
                'estoque_atual',
                'estoque_minimo',
                'ativo',
                'dt_atualizacao',
            ]
        )
        produto = Produto.objects.select_related('categoria').get(pk=produto.pk)
        return success_response(_produto_to_dict(produto), 'PRODUTO_UPDATED')
    except Produto.DoesNotExist:
        return error_response('Produto nao encontrado.', 'NOT_FOUND', 404)
    except IntegrityError:
        return error_response('Produto ja cadastrado nesta categoria.', 'CONFLICT', 409)
    except Exception as exc:
        return error_response(str(exc), 'SERVER_ERROR', 500)
