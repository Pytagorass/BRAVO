# =======================================================================
# 1. IMPORTAÇÕES
# =======================================================================
import json
import jwt
import datetime
import bcrypt 
from decimal import Decimal, InvalidOperation
from functools import wraps

# Importações do Django
from django.db import connection, IntegrityError, transaction
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.views.decorators.http import require_http_methods

# --- Importa decorador de autenticação ---
from .auth_decorator import token_required

# =======================================================================
# 2. FUNÇÕES UTILITÁRIAS (Helpers)
# =======================================================================

# -----------------------------------------------------------------------
# Função utilitária: dictfetchall
# Propósito: converter os resultados em formato lista de tuplas do cursor
#            em uma lista de dicionários, mantendo o nome da coluna como
#            chave. Isso simplifica a serialização em JSON.
# Parâmetros:
#   cursor -> instância aberta e já executada de um SELECT.
# Retorno:
#   Lista de dicionários compatível com as respostas utilizadas pelo front.
# Observação: evita repetição desse loop em cada view que consulta o banco.
def dictfetchall(cursor):
    """
    Converte o resultado de cursor.fetchall() em uma lista de dicionários.
    """
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]

# -----------------------------------------------------------------------
# Helper: is_valid_cpf
# Propósito: validar CPF informado pelo front antes de persistir no banco.
# Fluxo:
#   1. Remove tudo que não for dígito.
#   2. Verifica se possui 11 dígitos e não é uma sequência repetida.
#   3. Calcula os dígitos verificadores conforme regra oficial.
# Retorno:
#   True se o CPF é válido, False caso contrário.
def is_valid_cpf(value: str) -> bool:
    if not value:
        return False
    digits = ''.join(filter(str.isdigit, value))
    if len(digits) != 11 or digits == digits[0] * 11:
        return False

    def calc_digit(slice_len: int) -> int:
        total = sum(int(digits[i]) * ((slice_len + 2) - (i + 1)) for i in range(slice_len))
        resto = (total * 10) % 11
        return 0 if resto == 10 else resto

    return calc_digit(9) == int(digits[9]) and calc_digit(10) == int(digits[10])

#  =======================================================================
#  2B. HELPERS DE RESPOSTA PADRONIZADA
#  =======================================================================

# -----------------------------------------------------------------------
# Função utilitária: success_response
# Propósito: centralizar o formato de sucesso retornado ao React, evitando
#            divergências de contrato entre endpoints.
# Parâmetros:
#   data -> payload que será entregue à interface.
#   code -> string simbólica usada pelo front para logs/telemetria.
#   status_code -> HTTP status enviado ao cliente.
# Retorno:
#   JsonResponse com {"success": True, "data": ...}.
# Interação com o front-end: o axios interceptor confia nesse formato para
# definir toasts e popular componentes.
def success_response(data=None, code="OK", status_code=200):
    """
    Gera uma resposta JSON padronizada para SUCESSO seguindo o contrato oficial.
    """
    response = {
        "success": True,
        "data": data if data is not None else {}
    }
    return JsonResponse(response, status=status_code)

# -----------------------------------------------------------------------
# Função utilitária: error_response
# Propósito: padronizar a estrutura de erro, garantindo que o front consiga
# extrair `error.code` e `error.message`.
# Parâmetros:
#   message -> descrição amigável.
#   code -> código de erro categórico usado pelo front.
#   status_code -> status HTTP apropriado.
#   details -> payload opcional com dados extras (ex.: conflito de agenda).
# Retorno:
#   JsonResponse com {"success": False, "error": {...}}.
def error_response(message, code="ERRO_INTERNO", status_code=400, details=None):
    """
    Gera uma resposta JSON padronizada para ERRO seguindo o contrato oficial.
    """
    error_payload = {
        "code": code,
        "message": message
    }
    if details is not None:
        # 'details' pode conter o payload original ou dados de conflito
        error_payload["details"] = details
    return JsonResponse(
        {
            "success": False,
            "error": error_payload
        },
        status=status_code
    )


def _parse_required_int(data, field_name, message, code="VALIDATION_ERROR"):
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
        return datetime.datetime.strptime(value, "%Y-%m-%d").date(), None
    except (TypeError, ValueError):
        return None, error_response('Formato de data invalido. Use YYYY-MM-DD.', 'DATAS_OPERACAO_INVALIDAS', 400)


def _validar_operacao_reserva(cursor, data, acompanhante_ids, reserva_id_atual=None):
    barco_id, error = _parse_required_int(
        data,
        'fk_barco',
        'Selecione um barco para a reserva.',
        'BARCO_OBRIGATORIO'
    )
    if error:
        return None, error

    tipo_passeio_id, error = _parse_required_int(
        data,
        'fk_tipo_passeio',
        'Selecione o tipo de passeio da reserva.',
        'TIPO_PASSEIO_OBRIGATORIO'
    )
    if error:
        return None, error

    data_embarque, error = _parse_required_date(
        data,
        'data_embarque',
        'Data de embarque e obrigatoria.'
    )
    if error:
        return None, error

    data_desembarque, error = _parse_required_date(
        data,
        'data_desembarque',
        'Data de desembarque e obrigatoria.'
    )
    if error:
        return None, error

    if data_desembarque < data_embarque:
        return None, error_response(
            'Data de desembarque deve ser igual ou posterior ao embarque.',
            'DATAS_OPERACAO_INVALIDAS',
            400
        )

    cursor.execute(
        """
        SELECT nome_barco, capacidade_pessoas, status_barco
        FROM barco
        WHERE id_barco = %s
        FOR UPDATE;
        """,
        [barco_id]
    )
    barco = cursor.fetchone()
    if not barco:
        return None, error_response('Barco nao encontrado.', 'BARCO_NOT_FOUND', 404)

    nome_barco, capacidade_pessoas, status_barco = barco
    if status_barco != 'Disponível':
        return None, error_response(
            'Este barco nao esta disponivel para reserva.',
            'BARCO_INDISPONIVEL',
            409,
            {'nome_barco': nome_barco, 'status_barco': status_barco}
        )

    total_pessoas = 1 + len(acompanhante_ids)
    if total_pessoas > capacidade_pessoas:
        return None, error_response(
            'A quantidade de pessoas excede a capacidade do barco.',
            'CAPACIDADE_BARCO_EXCEDIDA',
            409,
            {
                'nome_barco': nome_barco,
                'capacidade_pessoas': capacidade_pessoas,
                'total_pessoas': total_pessoas
            }
        )

    cursor.execute(
        """
        SELECT nome_tipo
        FROM tipo_passeio
        WHERE id_tipo_passeio = %s AND ativo = 'Ativo';
        """,
        [tipo_passeio_id]
    )
    tipo_passeio = cursor.fetchone()
    if not tipo_passeio:
        return None, error_response('Tipo de passeio nao encontrado ou inativo.', 'TIPO_PASSEIO_INVALIDO', 404)

    params_conflito = [barco_id, data_embarque, data_desembarque]
    filtro_reserva_atual = ""
    if reserva_id_atual:
        filtro_reserva_atual = "AND r.id_reserva != %s"
        params_conflito.append(reserva_id_atual)

    sql_conflito_barco = f"""
        SELECT
            r.id_reserva,
            r.data_embarque,
            r.data_desembarque,
            h.nome_hospede AS nome_titular_conflito
        FROM reserva r
        LEFT JOIN hospede h ON r.fk_hospede_titular = h.id_hospede
        WHERE r.fk_barco = %s
          AND r.status_reserva != 'Cancelada'
          AND r.data_embarque IS NOT NULL
          AND r.data_desembarque IS NOT NULL
          AND daterange(r.data_embarque, r.data_desembarque + 1, '[)')
              && daterange(%s::date, %s::date + 1, '[)')
          {filtro_reserva_atual}
        LIMIT 1;
    """
    cursor.execute(sql_conflito_barco, params_conflito)
    conflito_barco = dictfetchall(cursor)
    if conflito_barco:
        return None, error_response(
            'Este barco ja esta reservado no periodo da viagem.',
            'BARCO_OVERBOOK',
            409,
            conflito_barco[0]
        )

    return {
        'fk_barco': barco_id,
        'fk_tipo_passeio': tipo_passeio_id,
        'data_embarque': data_embarque,
        'data_desembarque': data_desembarque,
        'local_embarque': data.get('local_embarque') or None,
        'local_desembarque': data.get('local_desembarque') or None,
        'observacao_operacional': data.get('observacao_operacional') or None,
        'nome_barco': nome_barco,
        'tipo_passeio': tipo_passeio[0],
    }, None

# =======================================================================
# 3. VIEWS DA API (Endpoints)
# =======================================================================

# -----------------------------------------------------------------
# Função: login_view
# Propósito: autenticar usuários administrativos e gerar JWT compatível
#            com o interceptor do front-end.
# Métodos aceitos: POST.
# Fluxo:
#   1. Lê e valida email/senha do body.
#   2. Consulta tabela `usuario`.
#   3. Compara hash com bcrypt.
#   4. Gera token com dados utilizados pela Sidebar/rotas protegidas.
# Integração front-end: Login.js consome `/api/login/` e armazena token +
# informações do usuário no localStorage.
# Impacto no banco: SELECT simples em `usuario`, sem mutações.
@csrf_exempt
@require_http_methods(["POST"])
def login_view(request):
    try:
        data = json.loads(request.body)
        email = data.get('email')
        senha_recebida = data.get('senha')

        if not email or not senha_recebida:
            # Validação básica para evitar hits desnecessários ao banco.
            return error_response('Email e senha são obrigatórios', 'VALIDATION_ERROR', 400)

        # Consulta responsável por autenticar usuários ativos; usada pela tela de Login
        # para gerar o JWT. Não há agregações, apenas SELECT simples em `usuario`.
        # SELECT usado na tela ClientesPage para listar hóspede por status.
        # Consulta da página QuartosPage: filtra quartos por status (Disponível/Manutenção).
        sql_query = """
            SELECT id_usuario, nome_usuario, email_usuario, tipo_usuario, senha 
            FROM usuario
            WHERE email_usuario = %s AND ativo = 'Ativo';
        """

        with connection.cursor() as cursor:
            cursor.execute(sql_query, [email])
            user_data = dictfetchall(cursor)

            if not user_data:
                return error_response('Credenciais inválidas ou usuário inativo', 'AUTH_FAILED', 401)

            usuario = user_data[0]
            senha_hash_bd = usuario['senha'].encode('utf-8')
            
            # Verificação da senha usando bcrypt
            if not bcrypt.checkpw(senha_recebida.encode('utf-8'), senha_hash_bd):
                return error_response('Credenciais inválidas', 'AUTH_FAILED', 401)

            # Geração do Payload e Token
            payload = {
                'id_usuario': usuario['id_usuario'],
                'email': usuario['email_usuario'],
                'tipo_usuario': usuario['tipo_usuario'],
                'nome': usuario['nome_usuario'],
                'exp': datetime.datetime.utcnow() + datetime.timedelta(days=1),
                'iat': datetime.datetime.utcnow()
            }
            token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')

            #  RESPOSTA PADRONIZADA
            response_data = {
                'token': token,
                'usuario': {
                    'id': usuario['id_usuario'],
                    'nome': usuario['nome_usuario'],
                    'email': usuario['email_usuario'],
                    'tipo': usuario['tipo_usuario']
                }
            }
            return success_response(response_data)

    except Exception as e:
        return error_response(f'Erro interno: {str(e)}', 'SERVER_ERROR', 500)

# -----------------------------------------------------------------
# Função: get_agenda_reservas
# Propósito: entregar o dataset utilizado pelo componente de Gantt no
# front-end (AgendaDashboard). Carrega reservas e quarto associado.
# Métodos aceitos: GET.
# Integração: `fetchAgendaReservas` em `services/api.js`.
# Observações:
#   - EndPoint protegido via JWT.
#   - Apenas realiza leitura (sem transação).
@csrf_exempt 
@token_required 
@require_http_methods(["GET"])
def get_agenda_reservas(request):

    # SELECT que alimenta o Gantt (AgendaDashboard). Busca reservas com check-in/out
    # e inclui dados de quarto e titular; sem agregações, apenas JOINs.
    sql_query = """
        SELECT
            rq.id_reserva_quarto, 
            rq.checkin, 
            rq.checkout,
            r.id_reserva, 
            r.status_reserva, 
            r.status_pagamento,
            r.fk_barco,
            r.fk_tipo_passeio,
            r.data_embarque,
            r.data_desembarque,
            r.local_embarque,
            r.local_desembarque,
            r.status_operacional,
            q.id_quarto, 
            q.numero AS numero_quarto,
            h.nome_hospede AS nome_titular,
            b.nome_barco,
            tp.nome_tipo AS tipo_passeio
        FROM 
            reserva_quarto AS rq
        INNER JOIN 
            reserva AS r ON rq.fk_reserva = r.id_reserva
        INNER JOIN 
            quarto AS q ON rq.fk_quarto = q.id_quarto
        LEFT JOIN
            hospede AS h ON r.fk_hospede_titular = h.id_hospede
        LEFT JOIN
            barco AS b ON r.fk_barco = b.id_barco
        LEFT JOIN
            tipo_passeio AS tp ON r.fk_tipo_passeio = tp.id_tipo_passeio

    """
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql_query)
            reservas = dictfetchall(cursor)
        
        #  RESPOSTA PADRONIZADA
        return success_response(reservas)

    except Exception as e:
        return error_response(str(e), 'SERVER_ERROR', 500)


# -----------------------------------------------------------------
# Status aceitos pelos enums operacionais no PostgreSQL.
STATUS_BARCO_VALIDOS = ('Disponível', 'Manutenção', 'Bloqueado')
STATUS_OPERACIONAL_VALIDOS = ('A Preparar', 'Pronto', 'Em Viagem', 'Finalizado')


def _validar_barco_payload(data):
    nome_barco = (data.get('nome_barco') or '').strip()
    status_barco = data.get('status_barco') or 'Disponível'
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


# Função: barcos_view
# Propósito: listar ou cadastrar barcos para a operação de viagem da reserva.
# Métodos aceitos: GET e POST.
# Integração front-end: `fetchBarcos`, `createBarco` e modal de reserva.
@csrf_exempt
@token_required
@require_http_methods(["GET", "POST"])
def barcos_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            barco_payload, error = _validar_barco_payload(data)
            if error:
                return error

            sql_insert = """
                INSERT INTO barco (
                    nome_barco,
                    capacidade_pessoas,
                    status_barco,
                    observacao
                )
                VALUES (%s, %s, %s, %s)
                RETURNING id_barco, nome_barco, capacidade_pessoas, status_barco, observacao, dt_criacao;
            """
            params = [
                barco_payload['nome_barco'],
                barco_payload['capacidade_pessoas'],
                barco_payload['status_barco'],
                barco_payload['observacao'],
            ]

            with connection.cursor() as cursor:
                cursor.execute(sql_insert, params)
                novo_barco = dictfetchall(cursor)[0]

            return success_response(novo_barco, 'BARCO_CREATED', 201)
        except IntegrityError as e:
            if 'barco_nome_barco_key' in str(e):
                return error_response(
                    f'Barco "{data.get("nome_barco")}" ja esta cadastrado.',
                    'CONFLICT',
                    409
                )
            return error_response(f'Erro de integridade: {str(e)}', 'DB_INTEGRITY_ERROR', 400)
        except Exception as e:
            return error_response(str(e), 'SERVER_ERROR', 500)

    status = request.GET.get('status')
    data_embarque = request.GET.get('data_embarque')
    data_desembarque = request.GET.get('data_desembarque')
    reserva_id = request.GET.get('reserva_id')
    status_params = []
    disponibilidade_params = []
    filtros = []

    if status:
        if status == 'Todos':
            status = None
        elif status not in STATUS_BARCO_VALIDOS:
            return error_response('Status de barco invalido.', 'VALIDATION_ERROR', 400)
        else:
            filtros.append("b.status_barco = %s")
            status_params.append(status)

    periodo_params = []
    reserva_id_param = None
    if data_embarque or data_desembarque:
        if not data_embarque or not data_desembarque:
            return error_response(
                'Informe data_embarque e data_desembarque para filtrar disponibilidade.',
                'DATAS_OPERACAO_INVALIDAS',
                400
            )

        try:
            embarque_date = datetime.datetime.strptime(data_embarque, "%Y-%m-%d").date()
            desembarque_date = datetime.datetime.strptime(data_desembarque, "%Y-%m-%d").date()
        except (TypeError, ValueError):
            return error_response('Formato de data invalido. Use YYYY-MM-DD.', 'DATAS_OPERACAO_INVALIDAS', 400)

        if desembarque_date < embarque_date:
            return error_response(
                'Data de desembarque deve ser igual ou posterior ao embarque.',
                'DATAS_OPERACAO_INVALIDAS',
                400
            )

        periodo_params = [embarque_date, desembarque_date]
        if reserva_id not in (None, ''):
            try:
                reserva_id_param = int(reserva_id)
            except (TypeError, ValueError):
                return error_response('reserva_id invalido.', 'VALIDATION_ERROR', 400)

    disponibilidade_select = ""
    disponibilidade_join = ""
    if periodo_params:
        disponibilidade_params.extend(periodo_params)
        disponibilidade_select = "COALESCE(conflitos.total_conflitos, 0) AS reservas_no_periodo,"
        filtros.append("COALESCE(conflitos.total_conflitos, 0) = 0")
        reserva_filter_sql = ""
        if reserva_id_param is not None:
            reserva_filter_sql = "AND r.id_reserva != %s"
            disponibilidade_params.append(reserva_id_param)
        disponibilidade_join = f"""
        LEFT JOIN LATERAL (
            SELECT COUNT(*) AS total_conflitos
            FROM reserva r
            WHERE r.fk_barco = b.id_barco
              AND r.status_reserva != 'Cancelada'
              AND r.data_embarque IS NOT NULL
              AND r.data_desembarque IS NOT NULL
              AND daterange(r.data_embarque, r.data_desembarque + 1, '[)')
                  && daterange(%s::date, %s::date + 1, '[)')
              {reserva_filter_sql}
        ) conflitos ON TRUE
        """

    if filtros:
        where_clause = "WHERE " + " AND ".join(filtros)
    else:
        where_clause = ""

    sql_query = f"""
        SELECT
            b.id_barco,
            b.nome_barco,
            b.capacidade_pessoas,
            b.status_barco,
            b.observacao,
            {disponibilidade_select}
            TRUE AS disponivel_periodo
        FROM barco b
        {disponibilidade_join}
        {where_clause}
        ORDER BY b.nome_barco;
    """

    try:
        with connection.cursor() as cursor:
            cursor.execute(sql_query, disponibilidade_params + status_params)
            barcos = dictfetchall(cursor)
        return success_response(barcos)
    except Exception as e:
        return error_response(str(e), 'SERVER_ERROR', 500)


# -----------------------------------------------------------------
# Função: barco_detail_view
# Propósito: consultar, editar e excluir um barco especifico.
# Métodos aceitos: GET, PUT e DELETE.
# Integração front-end: `fetchBarcoDetalhes`, `updateBarco`, `deleteBarco`.
@csrf_exempt
@token_required
@require_http_methods(["GET", "PUT", "DELETE"])
def barco_detail_view(request, barco_id):
    if request.method == 'GET':
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id_barco, nome_barco, capacidade_pessoas, status_barco, observacao, dt_criacao
                    FROM barco
                    WHERE id_barco = %s;
                    """,
                    [barco_id]
                )
                barco = dictfetchall(cursor)

            if not barco:
                return error_response('Barco nao encontrado.', 'NOT_FOUND', 404)

            return success_response(barco[0])
        except Exception as e:
            return error_response(str(e), 'SERVER_ERROR', 500)

    if request.method == 'PUT':
        try:
            data = json.loads(request.body)
            barco_payload, error = _validar_barco_payload(data)
            if error:
                return error

            sql_update = """
                UPDATE barco
                SET
                    nome_barco = %s,
                    capacidade_pessoas = %s,
                    status_barco = %s,
                    observacao = %s
                WHERE id_barco = %s
                RETURNING id_barco, nome_barco, capacidade_pessoas, status_barco, observacao, dt_criacao;
            """
            params = [
                barco_payload['nome_barco'],
                barco_payload['capacidade_pessoas'],
                barco_payload['status_barco'],
                barco_payload['observacao'],
                barco_id,
            ]

            with connection.cursor() as cursor:
                cursor.execute(sql_update, params)
                if cursor.rowcount == 0:
                    return error_response('Barco nao encontrado.', 'NOT_FOUND', 404)
                barco_atualizado = dictfetchall(cursor)[0]

            return success_response(barco_atualizado, 'BARCO_UPDATED')
        except IntegrityError as e:
            if 'barco_nome_barco_key' in str(e):
                return error_response(
                    f'Barco "{data.get("nome_barco")}" ja esta cadastrado.',
                    'CONFLICT',
                    409
                )
            return error_response(f'Erro de integridade: {str(e)}', 'DB_INTEGRITY_ERROR', 400)
        except Exception as e:
            return error_response(str(e), 'SERVER_ERROR', 500)

    if request.method == 'DELETE':
        try:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM barco WHERE id_barco = %s", [barco_id])
                if cursor.rowcount == 0:
                    return error_response('Barco nao encontrado.', 'NOT_FOUND', 404)

            return success_response(None, 'BARCO_DELETED', 204)
        except IntegrityError:
            return error_response(
                'Nao e possivel excluir este barco pois ele esta vinculado a uma ou mais reservas.',
                'FK_CONSTRAINT',
                409
            )
        except Exception as e:
            return error_response(str(e), 'SERVER_ERROR', 500)


# -----------------------------------------------------------------
# Função: tipos_passeio_view
# Propósito: listar tipos de passeio disponíveis para a reserva.
# Métodos aceitos: GET.
# Integração front-end: `fetchTiposPasseio` no modal de reserva.
@csrf_exempt
@token_required
@require_http_methods(["GET"])
def tipos_passeio_view(request):
    ativo = request.GET.get('ativo', 'Ativo')
    if ativo not in ['Ativo', 'Inativo', 'Todos']:
        ativo = 'Ativo'

    params = []
    where_clause = ""
    if ativo != 'Todos':
        where_clause = "WHERE ativo = %s"
        params.append(ativo)

    sql_query = f"""
        SELECT
            id_tipo_passeio,
            nome_tipo,
            descricao,
            ativo
        FROM tipo_passeio
        {where_clause}
        ORDER BY nome_tipo;
    """

    try:
        with connection.cursor() as cursor:
            cursor.execute(sql_query, params)
            tipos = dictfetchall(cursor)
        return success_response(tipos)
    except Exception as e:
        return error_response(str(e), 'SERVER_ERROR', 500)


# -----------------------------------------------------------------
# Função: reservas_view
# Propósito: criar novas reservas para o Gantt, garantindo consistência
#            das datas, quartos e hóspedes relacionados.
# Métodos aceitos: POST.
# Integração front-end: `createReserva` (NovaReservaModal).
# Impacto no banco: abre transação e grava em `reserva`, `reserva_quarto`
# e `reserva_hospede`, além de realizar locks em `quarto`.
@csrf_exempt
@token_required
@transaction.atomic  #  Garante que ou tudo (5 inserts) ou nada acontece
@require_http_methods(["POST"])
def reservas_view(request):
    """
    View para o POST: Cria uma nova reserva (transacional).

    Espera o seguinte payload JSON:"""
    try:
        data = json.loads(request.body)  # Payload enviado pelo React.

        try:
            # Titular obrigatório: conecta reserva ao responsável financeiro.
            titular_id = int(data.get('fk_hospede_id_hospede'))
        except (TypeError, ValueError):
            return error_response('Selecione um titular valido para a reserva.', 'TITULAR_OBRIGATORIO', 400)

        quartos_payload = data.get('quartos') or []
        try:
            # Modal sempre envia array; usamos o primeiro quarto selecionado.
            quarto_id = int(quartos_payload[0])
        except (IndexError, TypeError, ValueError):
            return error_response('Selecione um quarto valido.', 'QUARTO_INDISPONIVEL', 400)

        checkin = data.get('checkin')
        checkout = data.get('checkout')
        if not checkin or not checkout:
            # Sem datas não há como calcular diária nem verificar overbooking.
            return error_response('Datas de check-in e check-out sao obrigatorias.', 'DATAS_INVALIDAS', 400)

        try:
            checkin_date = datetime.datetime.strptime(checkin, "%Y-%m-%d").date()
            checkout_date = datetime.datetime.strptime(checkout, "%Y-%m-%d").date()
        except (TypeError, ValueError):
            return error_response('Formato de data invalido. Use YYYY-MM-DD.', 'DATAS_INVALIDAS', 400)

        if checkout_date <= checkin_date:
            return error_response('Checkout deve ser posterior ao checkin.', 'DATAS_INVALIDAS', 400)

        observacao = data.get('observacao_reserva')
        status_pagamento = data.get('status_pagamento') or 'Pendente'
        fk_usuario_logado = request.user_token_payload.get('id_usuario')

        try:
            # IDs dos acompanhantes são validados para evitar strings inválidas.
            acompanhante_ids = [int(ac_id) for ac_id in data.get('acompanhantes', []) if ac_id]
        except (TypeError, ValueError):
            return error_response('Lista de acompanhantes invalida.', 'VALIDATION_ERROR', 400)

        with connection.cursor() as cursor:
            # Lock pessimista no quarto garante consistência mesmo com múltiplos POSTs.
            cursor.execute("SELECT status_quarto, valor_diaria FROM quarto WHERE id_quarto = %s FOR UPDATE", [quarto_id])
            quarto_info = cursor.fetchone()
            if not quarto_info:
                return error_response('Quarto nao encontrado.', 'NOT_FOUND', 404)

            status_quarto, valor_diaria = quarto_info
            if status_quarto == 'Manutenção':
                return error_response('Quarto em manutencao nao pode ser reservado.', 'QUARTO_MANUTENCAO', 409)

            operacao_reserva, operacao_error = _validar_operacao_reserva(cursor, data, acompanhante_ids)
            if operacao_error:
                return operacao_error

            # Repete a checagem de overbooking para impedir conflitos futuros.
            # Consulta de validação para evitar overbooking; verifica se há reservas
            # que se sobrepõem ao período solicitado. Usada pelo formulário NovaReserva.
            sql_check_overbooking = """
                SELECT
                    rq.checkin,
                    rq.checkout,
                    h.nome_hospede AS nome_titular_conflito
                FROM reserva_quarto rq
                JOIN reserva r ON rq.fk_reserva = r.id_reserva
                LEFT JOIN hospede h ON r.fk_hospede_titular = h.id_hospede
                WHERE rq.fk_quarto = %s
                  AND (DATE %s, DATE %s) OVERLAPS (rq.checkin, rq.checkout)
                  AND r.status_reserva != 'Cancelada'
                LIMIT 1;
            """
            cursor.execute(sql_check_overbooking, [quarto_id, checkin, checkout])
            conflito = dictfetchall(cursor)
            if conflito:
                return error_response(
                    'Este quarto ja esta ocupado no periodo solicitado.',
                    'OVERBOOK',
                    409,
                    conflito[0]
                )

            # Número de diárias usado para calcular valor_total no back-end,
            # evitando manipulação maliciosa via front.
            diarias = (checkout_date - checkin_date).days
            valor_total = valor_diaria * diarias

            sql_reserva = """
                INSERT INTO reserva (
                    valor_total,
                    observacao_reserva,
                    fk_usuario,
                    status_reserva,
                    status_pagamento,
                    fk_hospede_titular,
                    fk_barco,
                    fk_tipo_passeio,
                    data_embarque,
                    data_desembarque,
                    local_embarque,
                    local_desembarque,
                    status_operacional,
                    observacao_operacional
                )
                VALUES (%s, %s, %s, 'Agendada', %s, %s, %s, %s, %s, %s, %s, %s, 'A Preparar', %s)
                RETURNING id_reserva;
            """
            params_reserva = [
                valor_total,
                observacao,
                fk_usuario_logado,
                status_pagamento,
                titular_id,
                operacao_reserva['fk_barco'],
                operacao_reserva['fk_tipo_passeio'],
                operacao_reserva['data_embarque'],
                operacao_reserva['data_desembarque'],
                operacao_reserva['local_embarque'],
                operacao_reserva['local_desembarque'],
                operacao_reserva['observacao_operacional'],
            ]
            cursor.execute(sql_reserva, params_reserva)
            nova_reserva_id = cursor.fetchone()[0]

            sql_quarto = """
                INSERT INTO reserva_quarto (
                    fk_reserva,
                    fk_quarto,
                    checkin,
                    checkout,
                    valor_diaria_cobrado
                )
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id_reserva_quarto;
            """
            params_quarto = [nova_reserva_id, quarto_id, checkin, checkout, valor_diaria]
            cursor.execute(sql_quarto, params_quarto)
            nova_reserva_quarto_id = cursor.fetchone()[0]

            if acompanhante_ids:
                sql_acompanhante = """
                    INSERT INTO reserva_hospede (fk_reserva, fk_hospede)
                    VALUES (%s, %s);
                """
                params_acompanhantes = [(nova_reserva_id, ac_id) for ac_id in acompanhante_ids]
                cursor.executemany(sql_acompanhante, params_acompanhantes)

            cursor.execute("SELECT nome_hospede FROM hospede WHERE id_hospede = %s", [titular_id])
            nome_titular = cursor.fetchone()[0]

            cursor.execute("SELECT numero FROM quarto WHERE id_quarto = %s", [quarto_id])
            numero_quarto = cursor.fetchone()[0]

        nova_reserva_obj = {
            'id_reserva_quarto': nova_reserva_quarto_id,
            'checkin': checkin,
            'checkout': checkout,
            'id_reserva': nova_reserva_id,
            'status_reserva': 'Agendada',
            'status_pagamento': status_pagamento,
            'id_quarto': quarto_id,
            'numero_quarto': numero_quarto,
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

        return success_response(nova_reserva_obj, status_code=201)

    except IntegrityError as e:
        return error_response(f'Erro de integridade no banco: {str(e)}', 'DB_INTEGRITY_ERROR', 400)

    except Exception as e:
        return error_response(str(e), 'ERRO_INTERNO', 500)

# -----------------------------------------------------------------
# Função: edit_reserva_view
# Propósito: atualizar reservas existentes (datas, quarto, hóspedes,
#            status de pagamento) diretamente pelo modal de edição.
# Métodos aceitos: PUT.
# Integração front-end: `updateReservaCompleta`.
# Impacto no banco: atualiza as tabelas `reserva`, `reserva_quarto` e
# `reserva_hospede` dentro de uma mesma transação.
@csrf_exempt
@token_required
@transaction.atomic
@require_http_methods(["PUT"])
def edit_reserva_view(request, reserva_quarto_id):
    try:
        data = json.loads(request.body)  # Payload enviado pelo modal de edição.

        try:
            titular_id = int(data.get('fk_hospede_id_hospede'))
        except (TypeError, ValueError):
            return error_response('Selecione um titular valido para a reserva.', 'TITULAR_OBRIGATORIO', 400)

        quartos_payload = data.get('quartos') or []
        try:
            quarto_id = int(quartos_payload[0])
        except (IndexError, TypeError, ValueError):
            return error_response('Selecione um quarto valido.', 'QUARTO_INDISPONIVEL', 400)

        checkin = data.get('checkin')
        checkout = data.get('checkout')
        if not checkin or not checkout:
            return error_response('Datas de check-in e check-out sao obrigatorias.', 'DATAS_INVALIDAS', 400)

        try:
            checkin_date = datetime.datetime.strptime(checkin, "%Y-%m-%d").date()
            checkout_date = datetime.datetime.strptime(checkout, "%Y-%m-%d").date()
        except (TypeError, ValueError):
            return error_response('Formato de data invalido. Use YYYY-MM-DD.', 'DATAS_INVALIDAS', 400)

        if checkout_date <= checkin_date:
            return error_response('Checkout deve ser posterior ao checkin.', 'DATAS_INVALIDAS', 400)

        observacao = data.get('observacao_reserva')
        status_pagamento = data.get('status_pagamento') or 'Pendente'
        fk_usuario_logado = request.user_token_payload.get('id_usuario')

        try:
            # IDs chegam como string do select múltiplo; convertemos para int.
            acompanhante_ids = [int(ac_id) for ac_id in data.get('acompanhantes', []) if ac_id]
        except (TypeError, ValueError):
            return error_response('Lista de acompanhantes invalida.', 'VALIDATION_ERROR', 400)

        with connection.cursor() as cursor:
            # Busca dados atuais da reserva e bloqueia a linha para edição segura.
            cursor.execute(
                """
                SELECT rq.fk_reserva, rq.fk_quarto, rq.checkin, rq.checkout, r.status_reserva
                FROM reserva_quarto rq
                JOIN reserva r ON rq.fk_reserva = r.id_reserva
                WHERE rq.id_reserva_quarto = %s
                FOR UPDATE
                """,
                [reserva_quarto_id]
            )
            reserva_data = cursor.fetchone()
            if not reserva_data:
                return error_response('Reserva (link quarto) nao encontrada.', 'NOT_FOUND', 404)

            id_reserva_principal, quarto_atual, checkin_atual, checkout_atual, status_reserva_atual = reserva_data

            if status_reserva_atual in ('Ativa', 'Concluda'):
                if checkin_atual.strftime("%Y-%m-%d") != checkin or checkout_atual.strftime("%Y-%m-%d") != checkout:
                    return error_response(
                        'Reservas ativas ou concluidas nao podem ter datas alteradas.',
                        'OPERACAO_NAO_PERMITIDA',
                        409
                    )

            # Garante que o novo quarto existe e pode ser reutilizado.
            cursor.execute("SELECT status_quarto, valor_diaria FROM quarto WHERE id_quarto = %s", [quarto_id])
            quarto_info = cursor.fetchone()
            if not quarto_info:
                return error_response('Quarto nao encontrado.', 'NOT_FOUND', 404)

            status_quarto, valor_diaria = quarto_info
            if status_quarto == 'Manutenção':
                return error_response('Quarto em manutencao nao pode ser reservado.', 'QUARTO_MANUTENCAO', 409)

            operacao_reserva, operacao_error = _validar_operacao_reserva(
                cursor,
                data,
                acompanhante_ids,
                reserva_id_atual=id_reserva_principal
            )
            if operacao_error:
                return operacao_error

            sql_check_overbooking = """
                SELECT 
                    rq.checkin, 
                    rq.checkout, 
                    h.nome_hospede AS nome_titular_conflito
                FROM reserva_quarto rq
                JOIN reserva r ON rq.fk_reserva = r.id_reserva
                LEFT JOIN hospede h ON r.fk_hospede_titular = h.id_hospede
                WHERE rq.fk_quarto = %s 
                  AND (DATE %s, DATE %s) OVERLAPS (rq.checkin, rq.checkout) 
                  AND r.status_reserva != 'Cancelada'
                  AND rq.id_reserva_quarto != %s
                LIMIT 1;
            """
            cursor.execute(sql_check_overbooking, [quarto_id, checkin, checkout, reserva_quarto_id])
            conflito = dictfetchall(cursor)
            if conflito:
                return error_response(
                    'Este quarto ja esta ocupado no periodo solicitado por outra reserva.',
                    'OVERBOOK',
                    409,
                    conflito[0]
                )

            diarias = (checkout_date - checkin_date).days
            valor_total = valor_diaria * diarias

            # Atualiza a reserva principal com valores recalculados.
            sql_update_reserva = """
                UPDATE reserva
                SET 
                    valor_total = %s,
                    observacao_reserva = %s,
                    fk_usuario = %s,
                    status_pagamento = %s,
                    fk_hospede_titular = %s,
                    fk_barco = %s,
                    fk_tipo_passeio = %s,
                    data_embarque = %s,
                    data_desembarque = %s,
                    local_embarque = %s,
                    local_desembarque = %s,
                    observacao_operacional = %s
                WHERE id_reserva = %s;
            """
            cursor.execute(
                sql_update_reserva,
                [
                    valor_total,
                    observacao,
                    fk_usuario_logado,
                    status_pagamento,
                    titular_id,
                    operacao_reserva['fk_barco'],
                    operacao_reserva['fk_tipo_passeio'],
                    operacao_reserva['data_embarque'],
                    operacao_reserva['data_desembarque'],
                    operacao_reserva['local_embarque'],
                    operacao_reserva['local_desembarque'],
                    operacao_reserva['observacao_operacional'],
                    id_reserva_principal,
                ]
            )

            # Atualiza o relacionamento com o quarto e datas efetivas.
            sql_update_rq = """
                UPDATE reserva_quarto
                SET
                    fk_quarto = %s, checkin = %s, checkout = %s,
                    valor_diaria_cobrado = %s
                WHERE id_reserva_quarto = %s;
            """
            cursor.execute(sql_update_rq, [quarto_id, checkin, checkout, valor_diaria, reserva_quarto_id])

            cursor.execute("DELETE FROM reserva_hospede WHERE fk_reserva = %s", [id_reserva_principal])
            if acompanhante_ids:
                # Reinsere acompanhantes conforme seleção atual do modal.
                sql_acompanhante = "INSERT INTO reserva_hospede (fk_reserva, fk_hospede) VALUES (%s, %s);"
                params_acompanhantes = [(id_reserva_principal, ac_id) for ac_id in acompanhante_ids]
                cursor.executemany(sql_acompanhante, params_acompanhantes)

            reserva_obj = _get_reserva_detalhes_internal(cursor, reserva_quarto_id)
            if not reserva_obj:
                return error_response('Reserva nao encontrada apos atualizacao.', 'NOT_FOUND', 404)

        return success_response(reserva_obj)

    except IntegrityError as e:
        return error_response(f'Erro de integridade no banco: {str(e)}', 'DB_INTEGRITY_ERROR', 400)

    except Exception as e:
        return error_response(str(e), 'ERRO_INTERNO', 500)

# -----------------------------------------------------------------
# Função: update_reserva_status_view
# Propósito: endpoint rápido para ações de "Marcar como Pago" ou "Cancelar"
# diretamente no cartão da agenda ou painel, incluindo status operacional.
# Métodos aceitos: PATCH.
# Fluxo: lê quais status foram enviados, bloqueia a linha principal de
# `reserva` e atualiza apenas os campos necessários.
# Integração front-end: `updateReservaStatus`.
@csrf_exempt
@token_required
@transaction.atomic
@require_http_methods(["PATCH"])
def update_reserva_status_view(request, reserva_quarto_id):
    try:
        data = json.loads(request.body)
        novo_status_reserva = data.get('status_reserva')
        novo_status_pagamento = data.get('status_pagamento')
        novo_status_operacional = data.get('status_operacional')

        if not novo_status_reserva and not novo_status_pagamento and not novo_status_operacional:
            return error_response('Nenhum status foi enviado para atualização.', 'VALIDATION_ERROR', 400)

        if novo_status_operacional and novo_status_operacional not in STATUS_OPERACIONAL_VALIDOS:
            return error_response('Status operacional invalido.', 'VALIDATION_ERROR', 400)

        with connection.cursor() as cursor:
            
            # Busca o ID da reserva principal para aplicar o UPDATE correto.
            cursor.execute("SELECT fk_reserva FROM reserva_quarto WHERE id_reserva_quarto = %s", [reserva_quarto_id])
            reserva_link = cursor.fetchone()
            if not reserva_link:
                return error_response('Reserva (link quarto) não encontrada.', 'NOT_FOUND', 404)
            
            id_reserva_principal = reserva_link[0]

            # Trava a linha da 'reserva' principal.
            cursor.execute("SELECT 1 FROM reserva WHERE id_reserva = %s FOR UPDATE", [id_reserva_principal])

            # Monta o SET dinamicamente para atualizar somente campos enviados.
            campos_para_atualizar = []
            params = []
            if novo_status_reserva:
                campos_para_atualizar.append("status_reserva = %s")
                params.append(novo_status_reserva)
            if novo_status_pagamento:
                campos_para_atualizar.append("status_pagamento = %s")
                params.append(novo_status_pagamento)
            if novo_status_operacional:
                campos_para_atualizar.append("status_operacional = %s")
                params.append(novo_status_operacional)

            # 4. Executa o UPDATE
            sql_update = f"UPDATE reserva SET {', '.join(campos_para_atualizar)} WHERE id_reserva = %s"
            params.append(id_reserva_principal)
            cursor.execute(sql_update, params)

            # 5. Retorna o objeto ATUALIZADO
            reserva_obj = _get_reserva_detalhes_internal(cursor, reserva_quarto_id)
            if not reserva_obj:
                 return error_response('Reserva não encontrada após atualização.', 'NOT_FOUND', 404)

        return success_response(reserva_obj, "STATUS_UPDATED")

    except Exception as e:
        return error_response(str(e), 'SERVER_ERROR', 500)


# -----------------------------------------------------------------
# Função: hospedes_view
# Propósito: CRUD simplificado para hóspedes utilizado nas telas de
# clientes e no modal de reserva.
# Métodos aceitos: GET (listagem filtrada por status) e POST (criação).
# Integração front-end: `fetchHospedes`, `createHospede`.
@csrf_exempt 
@token_required
@require_http_methods(["GET", "POST"])
def hospedes_view(request):
    
    # MÉTODO GET (Filtra por status Ativo/Inativo)
    if request.method == 'GET':
        status = request.GET.get('status', 'Ativo')
        if status not in ['Ativo', 'Inativo']:
            status = 'Ativo'

        sql_query = """
            SELECT id_hospede, nome_hospede, email_hospede, telefone, 
                   pais_origem, cpf, passaporte 
            FROM hospede 
            WHERE ativo = %s
            ORDER BY nome_hospede;
        """
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_query, [status])
                clientes = dictfetchall(cursor)
            return success_response(clientes)
        except Exception as e:
            return error_response(str(e), 'SERVER_ERROR', 500)

    # MÉTODO POST (Cria novo hóspede)
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Validações pré-insert: CPF obrigatório e com dígitos válidos para brasileiros.
            if data.get('pais_origem', 'Brasil') == 'Brasil':
                cpf = data.get('cpf')
                if not cpf:
                    return error_response("CPF é obrigatório para hóspedes do Brasil.", "VALIDATION_ERROR", 400)
                if not is_valid_cpf(cpf):
                    return error_response("Informe um CPF válido.", "VALIDATION_ERROR", 400)
            if data.get('pais_origem', 'Brasil') != 'Brasil' and not data.get('passaporte'):
                return error_response("Passaporte é obrigatório para hóspedes estrangeiros.", "VALIDATION_ERROR", 400)

            sql_insert = """
                INSERT INTO hospede (nome_hospede, email_hospede, telefone, pais_origem, cpf, passaporte)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING *; 
            """
            params = [
                data.get('nome_hospede'), data.get('email_hospede'), 
                data.get('telefone'), data.get('pais_origem', 'Brasil'), 
                data.get('cpf'), data.get('passaporte')
            ]

            with connection.cursor() as cursor:
                cursor.execute(sql_insert, params)
                novo_hospede = dictfetchall(cursor)[0]
            
            return success_response(novo_hospede, "HOSPEDE_CREATED", 201)
        
        except IntegrityError as e:
            return error_response(f'Erro de integridade: {str(e)}', 'DB_INTEGRITY_ERROR', 400)
        except Exception as e:
            return error_response(str(e), 'SERVER_ERROR', 500)

# -----------------------------------------------------------------
# Função: hospede_detail_view
# Propósito: operações de atualização, inativação ou reativação de um
# hóspede específico.
# Métodos aceitos: PUT (update), DELETE (inativar), PATCH (alterar status).
# Integração front-end: `updateHospede`, `deleteHospede`, `updateHospedeStatus`.
@csrf_exempt 
@token_required
@require_http_methods(["PUT", "DELETE", "PATCH"]) 
def hospede_detail_view(request, hospede_id):
    
    # MÉTODO PUT (Atualizar)
    if request.method == 'PUT':
        try:
            data = json.loads(request.body)
            
            # Validações na edição: reforça CPF válido para brasileiros.
            if data.get('pais_origem', 'Brasil') == 'Brasil':
                cpf = data.get('cpf')
                if not cpf:
                    return error_response("CPF é obrigatório para hóspedes do Brasil.", "VALIDATION_ERROR", 400)
                if not is_valid_cpf(cpf):
                    return error_response("Informe um CPF válido.", "VALIDATION_ERROR", 400)
            if data.get('pais_origem', 'Brasil') != 'Brasil' and not data.get('passaporte'):
                return error_response("Passaporte é obrigatório para hóspedes estrangeiros.", "VALIDATION_ERROR", 400)

            sql_update = """
                UPDATE hospede
                SET nome_hospede = %s, email_hospede = %s, telefone = %s, 
                    pais_origem = %s, cpf = %s, passaporte = %s
                WHERE id_hospede = %s
                RETURNING *;
            """
            params = [
                data.get('nome_hospede'), data.get('email_hospede'), 
                data.get('telefone'), data.get('pais_origem', 'Brasil'), 
                data.get('cpf'), data.get('passaporte'), 
                hospede_id
            ]
            
            with connection.cursor() as cursor:
                cursor.execute(sql_update, params)
                if cursor.rowcount == 0:
                    return error_response('Cliente não encontrado.', 'NOT_FOUND', 404)
                hospede_atualizado = dictfetchall(cursor)[0]
            
            return success_response(hospede_atualizado, "HOSPEDE_UPDATED")
        except IntegrityError as e:
            return error_response(f'Erro de integridade: {str(e)}', 'DB_INTEGRITY_ERROR', 400)
        except Exception as e:
            return error_response(str(e), 'SERVER_ERROR', 500)
            
    # MÉTODO DELETE (Inativar)
    elif request.method == 'DELETE':
        try:
            with connection.cursor() as cursor:
                sql_inativar = "UPDATE hospede SET ativo = 'Inativo' WHERE id_hospede = %s"
                cursor.execute(sql_inativar, [hospede_id])
                
                if cursor.rowcount == 0:
                    return error_response('Cliente nãoo encontrado com este ID.', 'NOT_FOUND', 404)
            
            return success_response(None, "HOSPEDE_INACTIVATED", 204) 
            
        except IntegrityError as e:
            return error_response(
                'Não é possível inativar este hóspede (erro de integridade).',
                'FK_CONSTRAINT', 409 
            )
        except Exception as e:
            return error_response(str(e), 'SERVER_ERROR', 500)
    
    # MÉTODO 'PATCH' (Reativar)
    elif request.method == 'PATCH':
        try:
            data = json.loads(request.body)
            novo_status = data.get('ativo')

            if novo_status not in ['Ativo', 'Inativo']:
                return error_response("Status inválido. Envie 'Ativo' ou 'Inativo'.", "VALIDATION_ERROR", 400)

            with connection.cursor() as cursor:
                sql_update = "UPDATE hospede SET ativo = %s WHERE id_hospede = %s"
                cursor.execute(sql_update, [novo_status, hospede_id])
                
                if cursor.rowcount == 0:
                    return error_response('Cliente não encontrado.', 'NOT_FOUND', 404)
            
            return success_response(None, "STATUS_UPDATED", 200) 

        except Exception as e:
            return error_response(str(e), 'SERVER_ERROR', 500)

# -----------------------------------------------------------------
# Função: usuario_perfil_view
# Propósito: recuperar e atualizar dados do usuário autenticado exibidos
# no modal de perfil do front-end.
# Métodos aceitos: GET para leitura e PUT para edição.
# Integração: `fetchUsuarioPerfil` e `updateUsuarioPerfil`.
@csrf_exempt 
@token_required
@require_http_methods(["GET", "PUT"])
def usuario_perfil_view(request):
    try:
        user_id = request.user_token_payload.get('id_usuario')
        if not user_id:
            return error_response('Token inválido, ID de usuário não encontrado.', 'INVALID_TOKEN', 401)
    except Exception as e:
        return error_response(f'Erro ao processar token: {str(e)}', 'INVALID_TOKEN', 401)

    with connection.cursor() as cursor:
        
        # MÉTODO GET: Buscar dados
        if request.method == 'GET':
            try:
                sql_get = "SELECT id_usuario, nome_usuario, email_usuario FROM usuario WHERE id_usuario = %s"
                cursor.execute(sql_get, [user_id])
                usuario = dictfetchall(cursor)
                
                if not usuario:
                    return error_response('Usuário não encontrado no banco.', 'NOT_FOUND', 404)
                
                return success_response(usuario[0])
            
            except Exception as e:
                return error_response(f'Erro no GET: {str(e)}', 'SERVER_ERROR', 500)

        # MÉTODO PUT: Atualizar o perfil
        elif request.method == 'PUT':
            try:
                data = json.loads(request.body)
                nome = data.get('nome_usuario')
                email = data.get('email_usuario')
                senha = data.get('senha') 

                sql_update_query = "UPDATE usuario SET nome_usuario = %s, email_usuario = %s"
                params = [nome, email]

                #  VULNERABILIDADE CORRIGIDA: Hashing da nova senha
                if senha:
                    hashed_senha = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt())
                    sql_update_query += ", senha = %s"
                    # Armazena o hash decodificado como string no BD
                    params.append(hashed_senha.decode('utf-8')) 

                sql_update_query += " WHERE id_usuario = %s"
                params.append(user_id)
                
                cursor.execute(sql_update_query, params)
                
                if cursor.rowcount == 0:
                    return error_response('Usuário não encontrado, nada atualizado.', 'NOT_FOUND', 404)

                return success_response(None, 'PROFILE_UPDATED')

            except IntegrityError as e:
                return error_response('Este e-mail já¡ está em uso por outra conta.', 'CONFLICT', 409)
            except Exception as e:
                return error_response(f'Erro no PUT: {str(e)}', 'SERVER_ERROR', 500)


# -----------------------------------------------------------------
# Função: get_reserva_detalhes
# Propósito: fornecer os dados completos consumidos pelo modal
# `ReservaDetalhesModal`, incluindo acompanhantes e histórico.
# Método aceito: GET.
# Impacto: apenas leitura com JOINs.
@csrf_exempt
@token_required
@require_http_methods(["GET"])
def get_reserva_detalhes(request, reserva_quarto_id):
    try:
        with connection.cursor() as cursor:
            detalhes = _get_reserva_detalhes_internal(cursor, reserva_quarto_id)
            
            if not detalhes:
                return error_response('Reserva não encontrada', 'NOT_FOUND', 404)
            
            return success_response(detalhes)

    except Exception as e:
        return error_response(str(e), 'SERVER_ERROR', 500)

# -----------------------------------------------------------------
#  FUNO INTERNA (Helper) para buscar detalhes da reserva
# -----------------------------------------------------------------
# -----------------------------------------------------------------
# Função auxiliar: _get_reserva_detalhes_internal
# Propósito: consulta reutilizada por múltiplas views para montar o shape
# retornado ao front (detalhes da reserva).
# Parâmetros:
#   cursor -> conexão já aberta/reutilizada.
#   reserva_quarto_id -> identificador do bloco no Gantt.
# Retorno: dicionário pronto para serialização.
def _get_reserva_detalhes_internal(cursor, reserva_quarto_id):

    detalhes = {}
    
    # Query 1: Busca os dados principais
    sql_detalhes = """
        SELECT
            r.id_reserva, r.valor_total, r.observacao_reserva, 
            r.status_reserva, r.status_pagamento, r.dt_criacao,
            r.fk_barco, r.fk_tipo_passeio, r.data_embarque, r.data_desembarque,
            r.local_embarque, r.local_desembarque, r.status_operacional,
            r.observacao_operacional,
            rq.id_reserva_quarto, rq.checkin, rq.checkout,
            q.id_quarto, q.numero AS numero_quarto, q.tipo_quarto,
            b.nome_barco, b.capacidade_pessoas AS capacidade_barco,
            tp.nome_tipo AS tipo_passeio,
            h.id_hospede AS id_titular,
            h.nome_hospede AS nome_titular,
            h.email_hospede AS email_titular,
            h.telefone AS telefone_titular,
            u.nome_usuario AS nome_usuario_criacao
        FROM 
            reserva_quarto AS rq
        JOIN reserva AS r ON rq.fk_reserva = r.id_reserva
        JOIN quarto AS q ON rq.fk_quarto = q.id_quarto
        LEFT JOIN barco AS b ON r.fk_barco = b.id_barco
        LEFT JOIN tipo_passeio AS tp ON r.fk_tipo_passeio = tp.id_tipo_passeio
        LEFT JOIN usuario AS u ON r.fk_usuario = u.id_usuario
        LEFT JOIN hospede AS h ON r.fk_hospede_titular = h.id_hospede
        WHERE 
            rq.id_reserva_quarto = %s;
    """
    cursor.execute(sql_detalhes, [reserva_quarto_id])
    detalhes_result = dictfetchall(cursor)
    
    if not detalhes_result:
        return None # Retorna None se não achar
    
    detalhes = detalhes_result[0]
    fk_reserva_principal = detalhes['id_reserva']
    
    # Query 2: Busca a lista de ACOMPANHANTES
    sql_acompanhantes = """
        SELECT h.id_hospede, h.nome_hospede
        FROM reserva_hospede AS rh
        JOIN hospede AS h ON rh.fk_hospede = h.id_hospede
        WHERE 
            rh.fk_reserva = %s;
    """
    cursor.execute(sql_acompanhantes, [fk_reserva_principal])
    acompanhantes = dictfetchall(cursor)
    
    detalhes['acompanhantes'] = acompanhantes
    return detalhes

# -----------------------------------------------------------------
# Função: quartos_view
# Propósito: consultar ou cadastrar quartos, utilizados tanto no módulo
# administrativo quanto no modal de reserva (para listar disponíveis).
# Métodos aceitos: GET e POST.
# Integração front-end: `fetchQuartos`, `createQuarto`.
@csrf_exempt 
@token_required
@require_http_methods(["GET", "POST"])
def quartos_view(request):
    
    # MÉTODO GET
    if request.method == 'GET':
         # O padrão é 'Disponível' se nada for fornecido.
        status = request.GET.get('status', 'Disponível')
        
        if status not in ['Disponível', 'Manutenção']:
            status = 'Disponível'

        #  MUDANA: A query agora usa um placeholder (%s) para o status
        sql_query = """
            SELECT
                id_quarto, numero, tipo_quarto, valor_diaria, status_quarto
            FROM quarto
            WHERE status_quarto = %s
            ORDER BY numero;
        """
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_query, [status])
                quartos = dictfetchall(cursor)
            return success_response(quartos)
        except Exception as e:
            return error_response(str(e), 'SERVER_ERROR', 500)

    # MÉTODO POST
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            sql_insert = """
                INSERT INTO quarto (numero, valor_diaria, tipo_quarto, status_quarto)
                VALUES (%s, %s, %s, %s)
                RETURNING *;
            """
            params = [data.get('numero'), data.get('valor_diaria'), data.get('tipo_quarto'), data.get('status_quarto', 'Disponível')]
            with connection.cursor() as cursor:
                cursor.execute(sql_insert, params)
                novo_quarto = dictfetchall(cursor)[0]
            return success_response(novo_quarto, "QUARTO_CREATED", 201)
        except IntegrityError as e:
            if 'quarto_numero_key' in str(e):
                return error_response(f'Erro: O número de quarto "{data.get("numero")}" já está cadastrado.', 'CONFLICT', 409)
            return error_response(f'Erro de integridade: {str(e)}', 'DB_INTEGRITY_ERROR', 400)
        except Exception as e:
            return error_response(str(e), 'SERVER_ERROR', 500)

# -----------------------------------------------------------------
# Função: quarto_detail_view
# Propósito: operações de leitura/atualização/remoção para um quarto
# específico selecionado na tela de manutenção.
# Métodos aceitos: GET, PUT e DELETE.
# Integração: `fetchQuartoDetalhes`, `updateQuarto`, `deleteQuarto`.
@csrf_exempt 
@token_required
@require_http_methods(["GET", "PUT", "DELETE"])
def quarto_detail_view(request, quarto_id):

    # MÉTODO GET (BY ID)
    if request.method == 'GET':
        try:
            with connection.cursor() as cursor:
                sql_get = "SELECT * FROM quarto WHERE id_quarto = %s"
                cursor.execute(sql_get, [quarto_id])
                quarto = dictfetchall(cursor)
                
                if not quarto:
                    return error_response('Quarto não encontrado.', 'NOT_FOUND', 404)
                
                return success_response(quarto[0])
        except Exception as e:
            return error_response(str(e), 'SERVER_ERROR', 500)

    # MÉTODO PUT (Atualizar)
    elif request.method == 'PUT':
        try:
            data = json.loads(request.body)
            
            numero = data.get('numero')
            valor_diaria = data.get('valor_diaria')
            tipo_quarto = data.get('tipo_quarto')
            status_db = data.get('status_quarto')

            if not numero or not valor_diaria or not tipo_quarto or not status_db:
                 return error_response('Todos os campos são obrigatórios.', 'VALIDATION_ERROR', 400)

            if status_db not in ['Disponível', 'Manutenção']:
                return error_response(f"Status '{status_db}' inválido. Use 'Disponível' ou 'Manutenção'.", "VALIDATION_ERROR", 400)
            
            sql_update = """
                UPDATE quarto
                SET 
                    numero = %s, 
                    valor_diaria = %s, 
                    tipo_quarto = %s, 
                    status_quarto = %s
                WHERE 
                    id_quarto = %s
                RETURNING id_quarto, numero, tipo_quarto, valor_diaria, status_quarto;
            """
            params = [numero, valor_diaria, tipo_quarto, status_db, quarto_id]

            with connection.cursor() as cursor:
                cursor.execute(sql_update, params)
                if cursor.rowcount == 0:
                    return error_response('Quarto não encontrado com este ID.', 'NOT_FOUND', 404)
                
                quarto_atualizado = dictfetchall(cursor)[0]

            return success_response(quarto_atualizado, "QUARTO_UPDATED")
        
        except IntegrityError as e:
            if 'quarto_numero_key' in str(e):
                return error_response(f'Erro: O número de quarto "{numero}" já está cadastrado.', 'CONFLICT', 409)
            return error_response(f'Erro de integridade: {str(e)}', 'DB_INTEGRITY_ERROR', 400)
        except Exception as e:
            return error_response(str(e), 'SERVER_ERROR', 500)

    # MÉTODO DELETE
    elif request.method == 'DELETE':
        try:
            #  CONTROLE DE INTEGRIDADE
            # Não podemos deletar um quarto que está em 'reserva_quarto'.
            # O PostgreSQL irá barrar com IntegrityError, que vamos capturar.
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM quarto WHERE id_quarto = %s", [quarto_id])
                if cursor.rowcount == 0:
                    return error_response('Quarto não encontrado com este ID.', 'NOT_FOUND', 404)
            
            # 204 Padrão para DELETE bem-sucedido
            return success_response(None, "QUARTO_DELETED", 204) 
            
        except IntegrityError as e:
            #  Erro pego! (fk_reserva_quarto_quarto)
            return error_response(
                'Não é possvel excluir este quarto pois ele está vinculado a uma ou mais reservas.',
                'FK_CONSTRAINT',
                409 # 409 Conflict
            )
        except Exception as e:
            return error_response(str(e), 'SERVER_ERROR', 500)

# =======================================================================
# 5. VIEW DE BUSINESS INTELLIGENCE (BI)
# =======================================================================

# -----------------------------------------------------------------
# Função: get_indicadores_gestao
# Propósito: alimentar o dashboard de gestão com KPIs de faturamento,
# ocupação, composição de reservas e demais gráficos avançados.
# Método aceito: GET.
# Integração front-end: `fetchIndicadoresGestao`.
# Observação: executa várias queries complexas (CTEs) e, por isso, faz
# tratamento cuidadoso de datas/ano filtrado.
@csrf_exempt
@token_required
@require_http_methods(["GET"])
def get_indicadores_gestao(request):

    try:
        try:
            ano_filtrar = int(request.GET.get('ano', datetime.datetime.now().year))
        except ValueError:
            ano_filtrar = datetime.datetime.now().year

        data_inicio = f"{ano_filtrar}-01-01"
        data_fim = f"{ano_filtrar}-12-31"

        kpi_data = {}
        faturamento_mensal = []
        taxa_ocupacao = {}
        faturamento_por_tipo = []
        reservas_por_status = []
        pagamentos_pendentes = {}
        consumo_resumo = {}
        consumo_por_origem = []
        produtos_mais_vendidos = []
        contas_consumo_abertas = []
        diarias_por_pais = []
        lead_time_medio = 0

        status_template = ['Agendada', 'Ativa', 'Concluda', 'Cancelada']

        with connection.cursor() as cursor:
            # KPIs exibidos nos cards superiores da tela de Gestão (soma faturamento e total de reservas).
            sql_kpi = """
                SELECT
                    COALESCE(SUM(r.valor_total), 0.00) AS faturamento_total,
                    COALESCE(COUNT(DISTINCT r.id_reserva), 0) AS total_reservas
                FROM reserva r
                INNER JOIN reserva_quarto rq ON r.id_reserva = rq.fk_reserva
                WHERE
                    r.status_reserva != 'Cancelada'
                    AND rq.checkin BETWEEN %s AND %s;
            """
            cursor.execute(sql_kpi, [data_inicio, data_fim])
            kpi_data = dictfetchall(cursor)[0]

            # CTE com 12 meses que alimenta o gráfico "Faturamento Mensal / Ocupação (%)".
            # Possui agregações para faturamento e dias ocupados, além de cálculo de taxa de ocupação.
            sql_mensal = """
                WITH meses AS (
                    SELECT date_trunc('month', (%s::date + (n || ' months')::interval)) AS mes
                    FROM generate_series(0, 11) AS n
                ),
                meses_formatados AS (
                    SELECT
                        mes,
                        TO_CHAR(mes, 'YYYY-MM') AS mes_ano,
                        EXTRACT(DAY FROM (mes + interval '1 month' - mes))::int AS dias_mes
                    FROM meses
                ),
                quartos_disponiveis AS (
                    SELECT COUNT(*) AS total_quartos
                    FROM quarto
                    WHERE status_quarto = 'Disponível'
                ),
                faturamento AS (
                    SELECT
                        TO_CHAR(rq.checkin, 'YYYY-MM') AS mes_ano,
                        SUM(r.valor_total) AS faturamento_mensal
                    FROM reserva r
                    JOIN reserva_quarto rq ON rq.fk_reserva = r.id_reserva
                    WHERE
                        r.status_reserva != 'Cancelada'
                        AND rq.checkin BETWEEN %s AND %s
                    GROUP BY 1
                ),
                ocupacao AS (
                    SELECT
                        TO_CHAR(date_trunc('month', dia), 'YYYY-MM') AS mes_ano,
                        COUNT(*)::numeric AS dias_ocupados
                    FROM reserva r
                    JOIN reserva_quarto rq ON rq.fk_reserva = r.id_reserva
                    CROSS JOIN LATERAL generate_series(
                        rq.checkin,
                        rq.checkout - interval '1 day',
                        interval '1 day'
                    ) AS dia
                    WHERE
                        r.status_reserva != 'Cancelada'
                        AND rq.checkin BETWEEN %s AND %s
                    GROUP BY 1
                )
                SELECT
                    mf.mes_ano,
                    COALESCE(f.faturamento_mensal, 0.00) AS faturamento_mensal,
                    COALESCE(o.dias_ocupados, 0) AS dias_ocupados,
                    (qd.total_quartos * mf.dias_mes) AS dias_disponiveis_mes,
                    CASE
                        WHEN (qd.total_quartos * mf.dias_mes) = 0 THEN 0
                        ELSE (COALESCE(o.dias_ocupados, 0) / (qd.total_quartos * mf.dias_mes)) * 100
                    END AS taxa_ocupacao_percent
                FROM meses_formatados mf
                CROSS JOIN quartos_disponiveis qd
                LEFT JOIN faturamento f ON f.mes_ano = mf.mes_ano
                LEFT JOIN ocupacao o ON o.mes_ano = mf.mes_ano
                ORDER BY mf.mes ASC;
            """
            cursor.execute(sql_mensal, [data_inicio, data_inicio, data_fim, data_inicio, data_fim])
            faturamento_mensal = dictfetchall(cursor)

            # Consulta auxiliar para o mesmo painel de Gestão: calcula taxa de ocupação anual
            # com base em dias vendidos versus dias disponíveis.
            sql_ocupacao = """
                WITH dias_disponiveis AS (
                    SELECT
                        (COUNT(id_quarto) * (%s::date - %s::date + 1)) AS total_dias_base
                    FROM quarto
                    WHERE status_quarto = 'Disponível'
                ),
                dias_vendidos_interval AS (
                    SELECT
                        COALESCE(SUM(
                            LEAST(rq.checkout, %s::date + interval '1 day') -
                            GREATEST(rq.checkin, %s::date)
                        ), INTERVAL '0 days') AS total_intervalo_vendido
                    FROM reserva_quarto rq
                    JOIN reserva r ON rq.fk_reserva = r.id_reserva
                    WHERE
                        r.status_reserva != 'Cancelada'
                        AND (rq.checkin, rq.checkout) OVERLAPS (%s::date, %s::date + interval '1 day')
                ),
                dias_vendidos AS (
                    SELECT
                        EXTRACT(EPOCH FROM total_intervalo_vendido) / 86400 AS total_dias_vendidos
                    FROM dias_vendidos_interval
                )
                SELECT
                    dv.total_dias_vendidos,
                    dd.total_dias_base,
                    CASE
                        WHEN dd.total_dias_base = 0 THEN 0
                        ELSE (dv.total_dias_vendidos / dd.total_dias_base) * 100
                    END AS taxa_ocupacao_percent
                FROM dias_disponiveis dd, dias_vendidos dv;
            """
            params_ocupacao = [
                data_fim, data_inicio,
                data_fim, data_inicio,
                data_inicio, data_fim
            ]
            cursor.execute(sql_ocupacao, params_ocupacao)
            taxa_ocupacao = dictfetchall(cursor)[0]

            # Alimenta o gráfico de rosca "Faturamento por tipo de quarto".
            sql_tipo_quarto = """
                SELECT
                    q.tipo_quarto,
                    COALESCE(SUM(r.valor_total), 0.00) AS faturamento_por_tipo
                FROM quarto q
                LEFT JOIN reserva_quarto rq ON q.id_quarto = rq.fk_quarto
                LEFT JOIN reserva r
                    ON rq.fk_reserva = r.id_reserva
                    AND r.status_reserva != 'Cancelada'
                    AND rq.checkin BETWEEN %s AND %s
                GROUP BY q.tipo_quarto
                ORDER BY faturamento_por_tipo DESC;
            """
            cursor.execute(sql_tipo_quarto, [data_inicio, data_fim])
            faturamento_por_tipo = dictfetchall(cursor)

            # Dados para o gráfico de barras que mostra quantidade de reservas por status.
            sql_reservas_status = """
                SELECT
                    r.status_reserva,
                    COUNT(DISTINCT r.id_reserva) AS total
                FROM reserva r
                JOIN reserva_quarto rq ON rq.fk_reserva = r.id_reserva
                WHERE (rq.checkin, rq.checkout) OVERLAPS (%s::date, %s::date + interval '1 day')
                GROUP BY r.status_reserva;
            """
            cursor.execute(sql_reservas_status, [data_inicio, data_fim])
            reservas_status_raw = dictfetchall(cursor)
            status_map = {row['status_reserva']: int(row['total']) for row in reservas_status_raw}
            reservas_por_status = [
                {
                    'status_reserva': status,
                    'total': status_map.get(status, 0)
                }
                for status in status_template
            ]

            # Valor total e contagem de reservas em aberto, exibidos no card "Pagamentos Pendentes".
            sql_pagamentos = """
                SELECT
                    COALESCE(SUM(r.valor_total), 0.00) AS valor_pendente,
                    COALESCE(COUNT(DISTINCT r.id_reserva), 0) AS reservas_em_aberto
                FROM reserva r
                JOIN reserva_quarto rq ON rq.fk_reserva = r.id_reserva
                WHERE
                    r.status_reserva != 'Cancelada'
                    AND r.status_pagamento IN ('Pendente','Em Partes')
                    AND (rq.checkin, rq.checkout) OVERLAPS (%s::date, %s::date + interval '1 day');
            """
            cursor.execute(sql_pagamentos, [data_inicio, data_fim])
            pagamentos_pendentes = dictfetchall(cursor)[0]

            # Indicadores do modulo de consumo (bebidas, lojinha e lavanderia)
            # para o painel executivo. Filtra os lancamentos confirmados no ano.
            sql_consumo_resumo = """
                WITH lancamentos_ano AS (
                    SELECT id_venda AS id_lancamento, total_venda AS total_lancamento
                    FROM venda_consumo
                    WHERE
                        status_venda = 'Confirmada'
                        AND dt_criacao::date BETWEEN %s AND %s
                    UNION ALL
                    SELECT id_ordem AS id_lancamento, total_ordem AS total_lancamento
                    FROM ordem_lavanderia
                    WHERE
                        status_ordem <> 'Cancelado'
                        AND dt_criacao::date BETWEEN %s AND %s
                ),
                contas_abertas AS (
                    SELECT
                        COUNT(*) AS contas_abertas,
                        COALESCE(SUM(total_acumulado), 0.00) AS total_contas_abertas
                    FROM conta_consumo
                    WHERE status_conta = 'Aberta'
                )
                SELECT
                    COALESCE(SUM(l.total_lancamento), 0.00) AS faturamento_total,
                    COALESCE(COUNT(l.id_lancamento), 0) AS total_vendas,
                    CASE
                        WHEN COUNT(l.id_lancamento) = 0 THEN 0.00
                        ELSE COALESCE(SUM(l.total_lancamento), 0.00) / COUNT(l.id_lancamento)
                    END AS ticket_medio,
                    ca.contas_abertas,
                    ca.total_contas_abertas
                FROM contas_abertas ca
                LEFT JOIN lancamentos_ano l ON TRUE
                GROUP BY ca.contas_abertas, ca.total_contas_abertas;
            """
            cursor.execute(sql_consumo_resumo, [data_inicio, data_fim, data_inicio, data_fim])
            consumo_resumo = dictfetchall(cursor)[0]

            sql_consumo_origem = """
                SELECT
                    origem,
                    COALESCE(COUNT(DISTINCT id_lancamento), 0) AS total_vendas,
                    COALESCE(SUM(total_lancamento), 0.00) AS faturamento,
                    COALESCE(SUM(quantidade_itens), 0) AS quantidade_itens
                FROM (
                    SELECT
                        vc.origem::text AS origem,
                        vc.id_venda AS id_lancamento,
                        vc.total_venda AS total_lancamento,
                        COALESCE(SUM(ivc.quantidade), 0) AS quantidade_itens
                    FROM venda_consumo vc
                    LEFT JOIN item_venda_consumo ivc ON ivc.fk_venda = vc.id_venda
                    WHERE
                        vc.status_venda = 'Confirmada'
                        AND vc.dt_criacao::date BETWEEN %s AND %s
                    GROUP BY vc.origem, vc.id_venda, vc.total_venda
                    UNION ALL
                    SELECT
                        'Lavanderia' AS origem,
                        ol.id_ordem AS id_lancamento,
                        ol.total_ordem AS total_lancamento,
                        COALESCE(SUM(iol.quantidade), 0) AS quantidade_itens
                    FROM ordem_lavanderia ol
                    LEFT JOIN item_ordem_lavanderia iol ON iol.fk_ordem = ol.id_ordem
                    WHERE
                        ol.status_ordem <> 'Cancelado'
                        AND ol.dt_criacao::date BETWEEN %s AND %s
                    GROUP BY ol.id_ordem, ol.total_ordem
                ) consumo
                GROUP BY origem
                ORDER BY faturamento DESC;
            """
            cursor.execute(sql_consumo_origem, [data_inicio, data_fim, data_inicio, data_fim])
            consumo_por_origem = dictfetchall(cursor)

            sql_produtos_mais_vendidos = """
                SELECT
                    id_produto,
                    nome_produto,
                    nome_categoria,
                    origem,
                    COALESCE(SUM(quantidade), 0) AS quantidade_total,
                    COALESCE(SUM(subtotal), 0.00) AS faturamento_total
                FROM (
                    SELECT
                        p.id_produto,
                        p.nome_produto,
                        cp.nome_categoria,
                        cp.tipo_categoria::text AS origem,
                        ivc.quantidade,
                        ivc.subtotal
                    FROM item_venda_consumo ivc
                    JOIN venda_consumo vc ON vc.id_venda = ivc.fk_venda
                    JOIN produto p ON p.id_produto = ivc.fk_produto
                    JOIN categoria_produto cp ON cp.id_categoria = p.fk_categoria
                    WHERE
                        vc.status_venda = 'Confirmada'
                        AND vc.dt_criacao::date BETWEEN %s AND %s
                    UNION ALL
                    SELECT
                        -sl.id_servico AS id_produto,
                        sl.nome_servico AS nome_produto,
                        cl.nome_categoria,
                        'Lavanderia' AS origem,
                        iol.quantidade,
                        iol.subtotal
                    FROM item_ordem_lavanderia iol
                    JOIN ordem_lavanderia ol ON ol.id_ordem = iol.fk_ordem
                    JOIN servico_lavanderia sl ON sl.id_servico = iol.fk_servico
                    JOIN categoria_lavanderia cl ON cl.id_categoria = sl.fk_categoria
                    WHERE
                        ol.status_ordem <> 'Cancelado'
                        AND ol.dt_criacao::date BETWEEN %s AND %s
                ) itens_consumo
                GROUP BY id_produto, nome_produto, nome_categoria, origem
                ORDER BY quantidade_total DESC, faturamento_total DESC
                LIMIT 8;
            """
            cursor.execute(sql_produtos_mais_vendidos, [data_inicio, data_fim, data_inicio, data_fim])
            produtos_mais_vendidos = dictfetchall(cursor)

            sql_contas_consumo_abertas = """
                SELECT
                    cc.id_conta,
                    r.id_reserva,
                    h.nome_hospede,
                    MIN(q.numero) AS numero_quarto,
                    cc.total_acumulado,
                    cc.dt_abertura
                FROM conta_consumo cc
                JOIN reserva r ON r.id_reserva = cc.fk_reserva
                LEFT JOIN hospede h ON h.id_hospede = r.fk_hospede_titular
                LEFT JOIN reserva_quarto rq ON rq.fk_reserva = r.id_reserva
                LEFT JOIN quarto q ON q.id_quarto = rq.fk_quarto
                WHERE cc.status_conta = 'Aberta'
                GROUP BY
                    cc.id_conta,
                    r.id_reserva,
                    h.nome_hospede,
                    cc.total_acumulado,
                    cc.dt_abertura
                ORDER BY cc.total_acumulado DESC, cc.dt_abertura ASC
                LIMIT 6;
            """
            cursor.execute(sql_contas_consumo_abertas)
            contas_consumo_abertas = dictfetchall(cursor)

        response_data = {
            'kpis': kpi_data,
            'taxa_ocupacao': taxa_ocupacao,
            'faturamento_mensal': faturamento_mensal,
            'faturamento_por_tipo': faturamento_por_tipo,
            'reservas_por_status': reservas_por_status,
            'pagamentos_pendentes': pagamentos_pendentes,
            'consumo_resumo': consumo_resumo,
            'consumo_por_origem': consumo_por_origem,
            'produtos_mais_vendidos': produtos_mais_vendidos,
            'contas_consumo_abertas': contas_consumo_abertas,
            'ano_filtrado': ano_filtrar
        }
        return success_response(response_data)

    except Exception as e:
        return error_response(str(e), 'SERVER_ERROR', 500)

# -----------------------------------------------------------------
# Função: get_reservas_pendentes
# Propósito: fornecer para o painel de gestão uma lista das reservas com
# pagamentos pendentes ou parciais, permitindo ações financeiras.
# Método aceito: GET.
# Integração: `fetchReservasPendentesGestao`.
@csrf_exempt
@token_required
@require_http_methods(["GET"])
def get_reservas_pendentes(request):
    """
    Retorna a lista de reservas com pagamentos pendentes ou parciais para o painel de Gestão.
    """
    try:
        with connection.cursor() as cursor:
            # Consulta usada no modal "Reservas pendentes" da tela de Gestão.
            # Sem agregações complexas, mas calcula `dias_desde_checkin` com NOW() para mostrar no front.
            sql = """
                SELECT
                    rq.id_reserva_quarto,
                    r.id_reserva,
                    r.status_reserva,
                    r.status_pagamento,
                    r.valor_total,
                    rq.checkin,
                    rq.checkout,
                    q.numero AS numero_quarto,
                    q.tipo_quarto,
                    h.nome_hospede AS titular,
                    h.telefone,
                    h.email_hospede,
                    GREATEST(
                        (NOW()::date - rq.checkin)::int,
                        0
                    ) AS dias_desde_checkin
                FROM reserva r
                JOIN reserva_quarto rq ON rq.fk_reserva = r.id_reserva
                LEFT JOIN quarto q ON rq.fk_quarto = q.id_quarto
                LEFT JOIN hospede h ON r.fk_hospede_titular = h.id_hospede
                WHERE
                    r.status_reserva != 'Cancelada'
                    AND r.status_pagamento IN ('Pendente','Em Partes')
                ORDER BY rq.checkin ASC;
            """
            cursor.execute(sql)
            reservas = dictfetchall(cursor)

        return success_response({'reservas': reservas})
    except Exception as e:
        return error_response(str(e), 'ERRO_INTERNO', 500)


# =======================================================================
# MODULO DE CONSUMO (BEBIDAS E LOJINHA)
# =======================================================================

TIPOS_CONSUMO_VALIDOS = ('Restaurante', 'Lojinha', 'Outros')
STATUS_ATIVO_VALIDOS = ('Ativo', 'Inativo')
CATEGORIA_BEBIDAS_CONSUMO = 'Bebidas'
STATUS_LAVANDERIA_VALIDOS = ('Recebido', 'Em Lavagem', 'Pronto', 'Entregue', 'Cancelado')


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
        if normalized in ('false', '0', 'nao', 'não', 'no'):
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

    fk_categoria, error = _parse_int(data.get('fk_categoria'), 'Categoria', 1)
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
        'fk_categoria': fk_categoria,
        'nome_produto': nome_produto,
        'descricao': descricao.strip() if isinstance(descricao, str) and descricao.strip() else None,
        'preco_atual': preco_atual,
        'controla_estoque': controla_estoque,
        'estoque_atual': estoque_atual,
        'estoque_minimo': estoque_minimo,
        'ativo': ativo,
    }, None


@csrf_exempt
@token_required
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
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO categoria_produto (nome_categoria, tipo_categoria, ativo)
                    VALUES (%s, %s, %s)
                    RETURNING id_categoria, nome_categoria, tipo_categoria, ativo, dt_criacao;
                    """,
                    [payload['nome_categoria'], payload['tipo_categoria'], payload['ativo']]
                )
                categoria = dictfetchall(cursor)[0]

            return success_response(categoria, 'CATEGORIA_CREATED', 201)
        except IntegrityError:
            return error_response('Categoria ja cadastrada para este tipo.', 'CONFLICT', 409)
        except Exception as e:
            return error_response(str(e), 'SERVER_ERROR', 500)

    tipo_categoria = request.GET.get('tipo_categoria') or request.GET.get('origem')
    ativo = request.GET.get('ativo') or 'Ativo'
    filtros = []
    params = []

    if tipo_categoria:
        if tipo_categoria not in TIPOS_CONSUMO_VALIDOS:
            return error_response('Tipo de categoria invalido.', 'VALIDATION_ERROR', 400)
        filtros.append('tipo_categoria = %s')
        params.append(tipo_categoria)

    if ativo != 'Todos':
        if ativo not in STATUS_ATIVO_VALIDOS:
            return error_response('Status da categoria invalido.', 'VALIDATION_ERROR', 400)
        filtros.append('ativo = %s')
        params.append(ativo)

    where_clause = f"WHERE {' AND '.join(filtros)}" if filtros else ''

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT id_categoria, nome_categoria, tipo_categoria, ativo, dt_criacao
                FROM categoria_produto
                {where_clause}
                ORDER BY tipo_categoria, nome_categoria;
                """,
                params
            )
            categorias = dictfetchall(cursor)

        return success_response(categorias)
    except Exception as e:
        return error_response(str(e), 'SERVER_ERROR', 500)


@csrf_exempt
@token_required
@require_http_methods(["GET", "POST"])
def consumo_produtos_view(request):
    if request.method == 'POST':
        data, parse_error = _parse_json_body(request)
        if parse_error:
            return parse_error

        payload, error = _validar_produto_consumo_payload(data)
        if error:
            return error

        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id_categoria, nome_categoria, tipo_categoria, ativo
                    FROM categoria_produto
                    WHERE id_categoria = %s;
                    """,
                    [payload['fk_categoria']]
                )
                categoria_result = dictfetchall(cursor)
                if not categoria_result:
                    return error_response('Categoria nao encontrada.', 'NOT_FOUND', 404)

                categoria = categoria_result[0]
                if categoria['ativo'] != 'Ativo':
                    return error_response('Categoria inativa para cadastro de produto.', 'CATEGORIA_INATIVA', 400)

                open_food_error = _validar_categoria_open_food(
                    categoria['tipo_categoria'],
                    categoria['nome_categoria'],
                )
                if open_food_error:
                    return open_food_error

                cursor.execute(
                    """
                    INSERT INTO produto (
                        fk_categoria,
                        nome_produto,
                        descricao,
                        preco_atual,
                        controla_estoque,
                        estoque_atual,
                        estoque_minimo,
                        ativo
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING
                        id_produto,
                        fk_categoria,
                        nome_produto,
                        descricao,
                        preco_atual::float AS preco_atual,
                        controla_estoque,
                        estoque_atual,
                        estoque_minimo,
                        ativo,
                        dt_criacao,
                        dt_atualizacao;
                    """,
                    [
                        payload['fk_categoria'],
                        payload['nome_produto'],
                        payload['descricao'],
                        payload['preco_atual'],
                        payload['controla_estoque'],
                        payload['estoque_atual'],
                        payload['estoque_minimo'],
                        payload['ativo'],
                    ]
                )
                produto = dictfetchall(cursor)[0]

            return success_response(produto, 'PRODUTO_CREATED', 201)
        except IntegrityError:
            return error_response('Produto ja cadastrado nesta categoria.', 'CONFLICT', 409)
        except Exception as e:
            return error_response(str(e), 'SERVER_ERROR', 500)

    origem = request.GET.get('origem') or request.GET.get('tipo_categoria')
    ativo = request.GET.get('ativo') or 'Ativo'
    filtros = []
    params = []

    if origem:
        if origem not in TIPOS_CONSUMO_VALIDOS:
            return error_response('Origem de consumo invalida.', 'VALIDATION_ERROR', 400)
        filtros.append('c.tipo_categoria = %s')
        params.append(origem)

    if ativo != 'Todos':
        if ativo not in STATUS_ATIVO_VALIDOS:
            return error_response('Status do produto invalido.', 'VALIDATION_ERROR', 400)
        filtros.append('p.ativo = %s')
        params.append(ativo)

    where_clause = f"WHERE {' AND '.join(filtros)}" if filtros else ''

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT
                    p.id_produto,
                    p.fk_categoria,
                    c.nome_categoria,
                    c.tipo_categoria,
                    p.nome_produto,
                    p.descricao,
                    p.preco_atual::float AS preco_atual,
                    p.controla_estoque,
                    p.estoque_atual,
                    p.estoque_minimo,
                    p.ativo,
                    p.dt_criacao,
                    p.dt_atualizacao
                FROM produto p
                JOIN categoria_produto c ON c.id_categoria = p.fk_categoria
                {where_clause}
                ORDER BY c.tipo_categoria, c.nome_categoria, p.nome_produto;
                """,
                params
            )
            produtos = dictfetchall(cursor)

        return success_response(produtos)
    except Exception as e:
        return error_response(str(e), 'SERVER_ERROR', 500)


@csrf_exempt
@token_required
@require_http_methods(["GET", "PUT", "PATCH"])
def consumo_produto_detail_view(request, produto_id):
    if request.method == 'GET':
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        p.id_produto,
                        p.fk_categoria,
                        c.nome_categoria,
                        c.tipo_categoria,
                        p.nome_produto,
                        p.descricao,
                        p.preco_atual::float AS preco_atual,
                        p.controla_estoque,
                        p.estoque_atual,
                        p.estoque_minimo,
                        p.ativo,
                        p.dt_criacao,
                        p.dt_atualizacao
                    FROM produto p
                    JOIN categoria_produto c ON c.id_categoria = p.fk_categoria
                    WHERE p.id_produto = %s;
                    """,
                    [produto_id]
                )
                produto = dictfetchall(cursor)

            if not produto:
                return error_response('Produto nao encontrado.', 'NOT_FOUND', 404)

            return success_response(produto[0])
        except Exception as e:
            return error_response(str(e), 'SERVER_ERROR', 500)

    data, parse_error = _parse_json_body(request)
    if parse_error:
        return parse_error

    if request.method == 'PATCH':
        ativo = data.get('ativo')
        if ativo not in STATUS_ATIVO_VALIDOS:
            return error_response('Status do produto invalido.', 'VALIDATION_ERROR', 400)

        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE produto
                    SET ativo = %s, dt_atualizacao = NOW()
                    WHERE id_produto = %s
                    RETURNING id_produto, ativo, dt_atualizacao;
                    """,
                    [ativo, produto_id]
                )
                produto = dictfetchall(cursor)

            if not produto:
                return error_response('Produto nao encontrado.', 'NOT_FOUND', 404)

            return success_response(produto[0], 'PRODUTO_STATUS_UPDATED')
        except Exception as e:
            return error_response(str(e), 'SERVER_ERROR', 500)

    payload, error = _validar_produto_consumo_payload(data)
    if error:
        return error

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id_categoria, nome_categoria, tipo_categoria, ativo
                FROM categoria_produto
                WHERE id_categoria = %s;
                """,
                [payload['fk_categoria']]
            )
            categoria_result = dictfetchall(cursor)
            if not categoria_result:
                return error_response('Categoria nao encontrada.', 'NOT_FOUND', 404)

            categoria = categoria_result[0]
            if categoria['ativo'] != 'Ativo':
                return error_response('Categoria inativa para cadastro de produto.', 'CATEGORIA_INATIVA', 400)

            open_food_error = _validar_categoria_open_food(
                categoria['tipo_categoria'],
                categoria['nome_categoria'],
            )
            if open_food_error:
                return open_food_error

            cursor.execute(
                """
                UPDATE produto
                SET
                    fk_categoria = %s,
                    nome_produto = %s,
                    descricao = %s,
                    preco_atual = %s,
                    controla_estoque = %s,
                    estoque_atual = %s,
                    estoque_minimo = %s,
                    ativo = %s,
                    dt_atualizacao = NOW()
                WHERE id_produto = %s
                RETURNING
                    id_produto,
                    fk_categoria,
                    nome_produto,
                    descricao,
                    preco_atual::float AS preco_atual,
                    controla_estoque,
                    estoque_atual,
                    estoque_minimo,
                    ativo,
                    dt_criacao,
                    dt_atualizacao;
                """,
                [
                    payload['fk_categoria'],
                    payload['nome_produto'],
                    payload['descricao'],
                    payload['preco_atual'],
                    payload['controla_estoque'],
                    payload['estoque_atual'],
                    payload['estoque_minimo'],
                    payload['ativo'],
                    produto_id,
                ]
            )
            produto = dictfetchall(cursor)

        if not produto:
            return error_response('Produto nao encontrado.', 'NOT_FOUND', 404)

        return success_response(produto[0], 'PRODUTO_UPDATED')
    except IntegrityError:
        return error_response('Produto ja cadastrado nesta categoria.', 'CONFLICT', 409)
    except Exception as e:
        return error_response(str(e), 'SERVER_ERROR', 500)


@csrf_exempt
@token_required
@require_http_methods(["GET"])
def consumo_reservas_abertas_view(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    r.id_reserva,
                    r.fk_hospede_titular AS id_hospede,
                    rq.id_quarto,
                    cc.id_conta,
                    h.nome_hospede,
                    q.numero AS numero_quarto,
                    r.status_reserva,
                    COALESCE(cc.status_conta::text, 'Sem Conta') AS status_conta,
                    COALESCE(cc.total_acumulado, 0)::float AS total_acumulado,
                    r.data_embarque,
                    r.data_desembarque,
                    r.status_operacional
                FROM reserva r
                LEFT JOIN LATERAL (
                    SELECT rq_inner.fk_quarto AS id_quarto
                    FROM reserva_quarto rq_inner
                    WHERE rq_inner.fk_reserva = r.id_reserva
                    ORDER BY rq_inner.checkin DESC
                    LIMIT 1
                ) rq ON TRUE
                LEFT JOIN quarto q ON q.id_quarto = rq.id_quarto
                LEFT JOIN hospede h ON h.id_hospede = r.fk_hospede_titular
                LEFT JOIN conta_consumo cc ON cc.fk_reserva = r.id_reserva
                WHERE r.status_reserva = 'Ativa'
                  AND (cc.id_conta IS NULL OR cc.status_conta = 'Aberta')
                ORDER BY q.numero, h.nome_hospede;
                """
            )
            reservas = dictfetchall(cursor)

        return success_response(reservas)
    except Exception as e:
        return error_response(str(e), 'SERVER_ERROR', 500)


def _buscar_ou_criar_conta_consumo(cursor, reserva_id):
    cursor.execute(
        """
        INSERT INTO conta_consumo (fk_reserva)
        VALUES (%s)
        ON CONFLICT (fk_reserva) DO UPDATE
            SET fk_reserva = EXCLUDED.fk_reserva
        RETURNING id_conta, status_conta;
        """,
        [reserva_id]
    )
    conta = dictfetchall(cursor)[0]

    if conta['status_conta'] != 'Aberta':
        return None, error_response('A conta de consumo desta reserva nao esta aberta.', 'CONTA_FECHADA', 409)

    return conta, None


def _buscar_ordens_lavanderia_por_conta(cursor, conta_id):
    cursor.execute(
        """
        SELECT
            ol.id_ordem,
            ol.fk_conta,
            ol.fk_reserva,
            ol.fk_usuario,
            ol.status_ordem,
            ol.observacao,
            ol.total_ordem::float AS total_ordem,
            ol.dt_recebimento,
            ol.dt_previsao_entrega,
            ol.dt_entrega,
            ol.dt_cancelamento,
            ol.dt_criacao
        FROM ordem_lavanderia ol
        WHERE ol.fk_conta = %s
        ORDER BY ol.dt_criacao DESC;
        """,
        [conta_id]
    )
    ordens = dictfetchall(cursor)

    cursor.execute(
        """
        SELECT
            iol.id_item,
            iol.fk_ordem,
            iol.fk_servico,
            cl.id_categoria,
            cl.nome_categoria,
            sl.nome_servico,
            iol.quantidade,
            iol.valor_unitario::float AS valor_unitario,
            iol.subtotal::float AS subtotal,
            iol.observacao,
            iol.dt_criacao
        FROM item_ordem_lavanderia iol
        JOIN servico_lavanderia sl ON sl.id_servico = iol.fk_servico
        JOIN categoria_lavanderia cl ON cl.id_categoria = sl.fk_categoria
        JOIN ordem_lavanderia ol ON ol.id_ordem = iol.fk_ordem
        WHERE ol.fk_conta = %s
        ORDER BY iol.dt_criacao ASC;
        """,
        [conta_id]
    )
    itens = dictfetchall(cursor)

    itens_por_ordem = {}
    for item in itens:
        itens_por_ordem.setdefault(item['fk_ordem'], []).append(item)

    for ordem in ordens:
        ordem['itens'] = itens_por_ordem.get(ordem['id_ordem'], [])

    return ordens


@csrf_exempt
@token_required
@require_http_methods(["GET"])
def consumo_lavanderia_categorias_view(request):
    ativo = request.GET.get('ativo') or 'Ativo'
    filtros = []
    params = []

    if ativo != 'Todos':
        if ativo not in STATUS_ATIVO_VALIDOS:
            return error_response('Status da categoria invalido.', 'VALIDATION_ERROR', 400)
        filtros.append('ativo = %s')
        params.append(ativo)

    where_clause = f"WHERE {' AND '.join(filtros)}" if filtros else ''

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT
                    id_categoria,
                    nome_categoria,
                    descricao,
                    ativo,
                    ordem_exibicao,
                    dt_criacao
                FROM categoria_lavanderia
                {where_clause}
                ORDER BY ordem_exibicao, nome_categoria;
                """,
                params
            )
            categorias = dictfetchall(cursor)

        return success_response(categorias)
    except Exception as e:
        return error_response(str(e), 'SERVER_ERROR', 500)


@csrf_exempt
@token_required
@require_http_methods(["GET"])
def consumo_lavanderia_servicos_view(request):
    ativo = request.GET.get('ativo') or 'Ativo'
    categoria_id = request.GET.get('fk_categoria') or request.GET.get('id_categoria')
    filtros = []
    params = []

    if ativo != 'Todos':
        if ativo not in STATUS_ATIVO_VALIDOS:
            return error_response('Status do servico invalido.', 'VALIDATION_ERROR', 400)
        filtros.append('sl.ativo = %s')
        params.append(ativo)

    if categoria_id:
        categoria_id, error = _parse_int(categoria_id, 'Categoria', 1)
        if error:
            return error
        filtros.append('sl.fk_categoria = %s')
        params.append(categoria_id)

    where_clause = f"WHERE {' AND '.join(filtros)}" if filtros else ''

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT
                    sl.id_servico,
                    sl.fk_categoria,
                    cl.nome_categoria,
                    sl.nome_servico,
                    sl.descricao,
                    sl.preco_unitario::float AS preco_unitario,
                    sl.prazo_horas,
                    sl.ativo,
                    sl.dt_criacao,
                    sl.dt_atualizacao
                FROM servico_lavanderia sl
                JOIN categoria_lavanderia cl ON cl.id_categoria = sl.fk_categoria
                {where_clause}
                ORDER BY cl.ordem_exibicao, cl.nome_categoria, sl.nome_servico;
                """,
                params
            )
            servicos = dictfetchall(cursor)

        return success_response(servicos)
    except Exception as e:
        return error_response(str(e), 'SERVER_ERROR', 500)


@csrf_exempt
@token_required
@transaction.atomic
@require_http_methods(["GET", "POST"])
def consumo_lavanderia_ordens_view(request):
    if request.method == 'GET':
        status = request.GET.get('status')
        conta_id = request.GET.get('fk_conta') or request.GET.get('id_conta')
        reserva_id = request.GET.get('fk_reserva') or request.GET.get('id_reserva')
        filtros = []
        params = []

        if status:
            if status not in STATUS_LAVANDERIA_VALIDOS:
                return error_response('Status de lavanderia invalido.', 'VALIDATION_ERROR', 400)
            filtros.append('ol.status_ordem = %s')
            params.append(status)

        if conta_id:
            conta_id, error = _parse_int(conta_id, 'Conta', 1)
            if error:
                return error
            filtros.append('ol.fk_conta = %s')
            params.append(conta_id)

        if reserva_id:
            reserva_id, error = _parse_int(reserva_id, 'Reserva', 1)
            if error:
                return error
            filtros.append('ol.fk_reserva = %s')
            params.append(reserva_id)

        where_clause = f"WHERE {' AND '.join(filtros)}" if filtros else ''

        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT DISTINCT ol.fk_conta
                    FROM ordem_lavanderia ol
                    {where_clause}
                    ORDER BY ol.fk_conta;
                    """,
                    params
                )
                contas = [row[0] for row in cursor.fetchall()]

                ordens = []
                for conta in contas:
                    ordens.extend(_buscar_ordens_lavanderia_por_conta(cursor, conta))

            if status:
                ordens = [ordem for ordem in ordens if ordem['status_ordem'] == status]
            if reserva_id:
                ordens = [ordem for ordem in ordens if ordem['fk_reserva'] == reserva_id]

            return success_response(ordens)
        except Exception as e:
            return error_response(str(e), 'SERVER_ERROR', 500)

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
    observacao = data.get('observacao')

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id_reserva, status_reserva
                FROM reserva
                WHERE id_reserva = %s
                FOR UPDATE;
                """,
                [reserva_id]
            )
            reserva = dictfetchall(cursor)
            if not reserva:
                return error_response('Reserva nao encontrada.', 'NOT_FOUND', 404)
            if reserva[0]['status_reserva'] != 'Ativa':
                return error_response('Apenas reservas ativas podem receber lavanderia.', 'RESERVA_INATIVA', 409)

            conta, conta_error = _buscar_ou_criar_conta_consumo(cursor, reserva_id)
            if conta_error:
                return conta_error

            itens_processados = []
            total_ordem = Decimal('0.00')
            maior_prazo = 24

            for item in itens:
                servico_id = item.get('fk_servico') or item.get('id_servico')
                servico_id, error = _parse_int(servico_id, 'Servico', 1)
                if error:
                    return error

                quantidade, error = _parse_int(item.get('quantidade'), 'Quantidade', 1)
                if error:
                    return error

                cursor.execute(
                    """
                    SELECT
                        sl.id_servico,
                        sl.nome_servico,
                        sl.preco_unitario,
                        sl.prazo_horas,
                        cl.nome_categoria
                    FROM servico_lavanderia sl
                    JOIN categoria_lavanderia cl ON cl.id_categoria = sl.fk_categoria
                    WHERE sl.id_servico = %s
                      AND sl.ativo = 'Ativo'
                      AND cl.ativo = 'Ativo';
                    """,
                    [servico_id]
                )
                servico_result = dictfetchall(cursor)
                if not servico_result:
                    return error_response('Servico de lavanderia nao encontrado ou inativo.', 'SERVICO_INATIVO', 404)

                servico = servico_result[0]
                valor_unitario = servico['preco_unitario']
                subtotal = valor_unitario * quantidade
                total_ordem += subtotal
                maior_prazo = max(maior_prazo, int(servico['prazo_horas'] or 24))

                itens_processados.append({
                    'id_servico': servico_id,
                    'nome_servico': servico['nome_servico'],
                    'nome_categoria': servico['nome_categoria'],
                    'quantidade': quantidade,
                    'valor_unitario': valor_unitario,
                    'subtotal': subtotal,
                    'observacao': item.get('observacao'),
                })

            cursor.execute(
                """
                INSERT INTO ordem_lavanderia (
                    fk_conta,
                    fk_reserva,
                    fk_usuario,
                    observacao,
                    total_ordem,
                    dt_previsao_entrega
                )
                VALUES (%s, %s, %s, %s, %s, NOW() + (%s * INTERVAL '1 hour'))
                RETURNING
                    id_ordem,
                    fk_conta,
                    fk_reserva,
                    fk_usuario,
                    status_ordem,
                    observacao,
                    total_ordem::float AS total_ordem,
                    dt_recebimento,
                    dt_previsao_entrega,
                    dt_entrega,
                    dt_cancelamento,
                    dt_criacao;
                """,
                [
                    conta['id_conta'],
                    reserva_id,
                    usuario_id,
                    observacao.strip() if isinstance(observacao, str) and observacao.strip() else None,
                    total_ordem,
                    maior_prazo,
                ]
            )
            ordem = dictfetchall(cursor)[0]

            itens_response = []
            for item in itens_processados:
                cursor.execute(
                    """
                    INSERT INTO item_ordem_lavanderia (
                        fk_ordem,
                        fk_servico,
                        quantidade,
                        valor_unitario,
                        subtotal,
                        observacao
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING
                        id_item,
                        fk_ordem,
                        fk_servico,
                        quantidade,
                        valor_unitario::float AS valor_unitario,
                        subtotal::float AS subtotal,
                        observacao,
                        dt_criacao;
                    """,
                    [
                        ordem['id_ordem'],
                        item['id_servico'],
                        item['quantidade'],
                        item['valor_unitario'],
                        item['subtotal'],
                        item['observacao'],
                    ]
                )
                item_salvo = dictfetchall(cursor)[0]
                item_salvo['nome_servico'] = item['nome_servico']
                item_salvo['nome_categoria'] = item['nome_categoria']
                itens_response.append(item_salvo)

            cursor.execute(
                """
                INSERT INTO historico_lavanderia_status (
                    fk_ordem,
                    status_anterior,
                    status_novo,
                    fk_usuario,
                    observacao
                )
                VALUES (%s, NULL, 'Recebido', %s, %s);
                """,
                [ordem['id_ordem'], usuario_id, 'Ordem criada pelo app mobile']
            )

            cursor.execute(
                """
                UPDATE conta_consumo
                SET total_acumulado = total_acumulado + %s
                WHERE id_conta = %s
                RETURNING total_acumulado::float AS total_acumulado;
                """,
                [total_ordem, conta['id_conta']]
            )
            conta_atualizada = dictfetchall(cursor)[0]

        ordem['itens'] = itens_response
        ordem['total_acumulado_conta'] = conta_atualizada['total_acumulado']
        return success_response(ordem, 'ORDEM_LAVANDERIA_CREATED', 201)
    except Exception as e:
        return error_response(str(e), 'SERVER_ERROR', 500)


@csrf_exempt
@token_required
@transaction.atomic
@require_http_methods(["POST"])
def consumo_lavanderia_ordem_status_view(request, ordem_id):
    data, parse_error = _parse_json_body(request)
    if parse_error:
        return parse_error

    novo_status = data.get('status_ordem') or data.get('status')
    if novo_status not in STATUS_LAVANDERIA_VALIDOS:
        return error_response('Status de lavanderia invalido.', 'VALIDATION_ERROR', 400)

    observacao = data.get('observacao')
    usuario_id = request.user_token_payload.get('id_usuario')

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id_ordem, fk_conta, status_ordem, total_ordem
                FROM ordem_lavanderia
                WHERE id_ordem = %s
                FOR UPDATE;
                """,
                [ordem_id]
            )
            ordem_result = dictfetchall(cursor)
            if not ordem_result:
                return error_response('Ordem de lavanderia nao encontrada.', 'NOT_FOUND', 404)

            ordem_atual = ordem_result[0]
            status_anterior = ordem_atual['status_ordem']

            if status_anterior == novo_status:
                return success_response(ordem_atual, 'ORDEM_LAVANDERIA_STATUS_UNCHANGED')

            set_clauses = ['status_ordem = %s']
            params = [novo_status]

            if novo_status == 'Entregue':
                set_clauses.append('dt_entrega = COALESCE(dt_entrega, NOW())')
            if novo_status == 'Cancelado':
                set_clauses.append('dt_cancelamento = COALESCE(dt_cancelamento, NOW())')

            params.append(ordem_id)
            cursor.execute(
                f"""
                UPDATE ordem_lavanderia
                SET {', '.join(set_clauses)}
                WHERE id_ordem = %s
                RETURNING
                    id_ordem,
                    fk_conta,
                    fk_reserva,
                    fk_usuario,
                    status_ordem,
                    observacao,
                    total_ordem::float AS total_ordem,
                    dt_recebimento,
                    dt_previsao_entrega,
                    dt_entrega,
                    dt_cancelamento,
                    dt_criacao;
                """,
                params
            )
            ordem = dictfetchall(cursor)[0]

            if novo_status == 'Cancelado' and status_anterior != 'Cancelado':
                cursor.execute(
                    """
                    UPDATE conta_consumo
                    SET total_acumulado = GREATEST(total_acumulado - %s, 0)
                    WHERE id_conta = %s;
                    """,
                    [ordem_atual['total_ordem'], ordem_atual['fk_conta']]
                )

            cursor.execute(
                """
                INSERT INTO historico_lavanderia_status (
                    fk_ordem,
                    status_anterior,
                    status_novo,
                    fk_usuario,
                    observacao
                )
                VALUES (%s, %s, %s, %s, %s);
                """,
                [
                    ordem_id,
                    status_anterior,
                    novo_status,
                    usuario_id,
                    observacao.strip() if isinstance(observacao, str) and observacao.strip() else None,
                ]
            )

        return success_response(ordem, 'ORDEM_LAVANDERIA_STATUS_UPDATED')
    except Exception as e:
        return error_response(str(e), 'SERVER_ERROR', 500)


@csrf_exempt
@token_required
@transaction.atomic
@require_http_methods(["POST"])
def consumo_vendas_view(request):
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
    observacao = data.get('observacao')

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id_reserva, status_reserva
                FROM reserva
                WHERE id_reserva = %s
                FOR UPDATE;
                """,
                [reserva_id]
            )
            reserva = dictfetchall(cursor)
            if not reserva:
                return error_response('Reserva nao encontrada.', 'NOT_FOUND', 404)
            if reserva[0]['status_reserva'] != 'Ativa':
                return error_response('Apenas reservas ativas podem receber consumo.', 'RESERVA_INATIVA', 409)

            conta, conta_error = _buscar_ou_criar_conta_consumo(cursor, reserva_id)
            if conta_error:
                return conta_error

            itens_processados = []
            total_venda = Decimal('0.00')

            for item in itens:
                produto_id = item.get('fk_produto') or item.get('id_produto')
                produto_id, error = _parse_int(produto_id, 'Produto', 1)
                if error:
                    return error

                quantidade, error = _parse_int(item.get('quantidade'), 'Quantidade', 1)
                if error:
                    return error

                cursor.execute(
                    """
                    SELECT
                        p.id_produto,
                        p.nome_produto,
                        p.preco_atual,
                        p.controla_estoque,
                        p.estoque_atual,
                        c.tipo_categoria,
                        c.nome_categoria
                    FROM produto p
                    JOIN categoria_produto c ON c.id_categoria = p.fk_categoria
                    WHERE p.id_produto = %s
                      AND p.ativo = 'Ativo'
                      AND c.ativo = 'Ativo'
                    FOR UPDATE;
                    """,
                    [produto_id]
                )
                produto_result = dictfetchall(cursor)
                if not produto_result:
                    return error_response('Produto nao encontrado ou inativo.', 'PRODUTO_INATIVO', 404)

                produto = produto_result[0]
                if produto['tipo_categoria'] != origem:
                    return error_response(
                        'Produto nao pertence a origem informada para a venda.',
                        'PRODUTO_ORIGEM_INVALIDA',
                        400,
                        {
                            'id_produto': produto_id,
                            'origem_venda': origem,
                            'origem_produto': produto['tipo_categoria'],
                        }
                    )

                open_food_error = _validar_categoria_open_food(
                    produto['tipo_categoria'],
                    produto['nome_categoria'],
                )
                if open_food_error:
                    return open_food_error

                if produto['controla_estoque'] and produto['estoque_atual'] < quantidade:
                    return error_response(
                        'Estoque insuficiente para o produto.',
                        'ESTOQUE_INSUFICIENTE',
                        409,
                        {
                            'id_produto': produto_id,
                            'nome_produto': produto['nome_produto'],
                            'estoque_atual': produto['estoque_atual'],
                            'quantidade_solicitada': quantidade,
                        }
                    )

                valor_unitario = produto['preco_atual']
                subtotal = valor_unitario * quantidade
                total_venda += subtotal
                itens_processados.append({
                    'id_produto': produto_id,
                    'nome_produto': produto['nome_produto'],
                    'quantidade': quantidade,
                    'valor_unitario': valor_unitario,
                    'subtotal': subtotal,
                    'observacao': item.get('observacao'),
                    'controla_estoque': produto['controla_estoque'],
                    'estoque_atual': produto['estoque_atual'],
                })

            cursor.execute(
                """
                INSERT INTO venda_consumo (
                    fk_conta,
                    fk_reserva,
                    fk_usuario,
                    origem,
                    observacao,
                    total_venda
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING
                    id_venda,
                    fk_conta,
                    fk_reserva,
                    fk_usuario,
                    origem,
                    status_venda,
                    observacao,
                    total_venda::float AS total_venda,
                    dt_criacao;
                """,
                [
                    conta['id_conta'],
                    reserva_id,
                    usuario_id,
                    origem,
                    observacao.strip() if isinstance(observacao, str) and observacao.strip() else None,
                    total_venda,
                ]
            )
            venda = dictfetchall(cursor)[0]

            itens_response = []
            for item in itens_processados:
                cursor.execute(
                    """
                    INSERT INTO item_venda_consumo (
                        fk_venda,
                        fk_produto,
                        quantidade,
                        valor_unitario,
                        subtotal,
                        observacao
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING
                        id_item,
                        fk_venda,
                        fk_produto,
                        quantidade,
                        valor_unitario::float AS valor_unitario,
                        subtotal::float AS subtotal,
                        observacao,
                        dt_criacao;
                    """,
                    [
                        venda['id_venda'],
                        item['id_produto'],
                        item['quantidade'],
                        item['valor_unitario'],
                        item['subtotal'],
                        item['observacao'],
                    ]
                )
                item_salvo = dictfetchall(cursor)[0]
                item_salvo['nome_produto'] = item['nome_produto']
                itens_response.append(item_salvo)

                if item['controla_estoque']:
                    estoque_anterior = item['estoque_atual']
                    estoque_posterior = estoque_anterior - item['quantidade']
                    cursor.execute(
                        """
                        UPDATE produto
                        SET estoque_atual = %s, dt_atualizacao = NOW()
                        WHERE id_produto = %s;
                        """,
                        [estoque_posterior, item['id_produto']]
                    )
                    cursor.execute(
                        """
                        INSERT INTO movimento_estoque (
                            fk_produto,
                            fk_usuario,
                            fk_item_venda,
                            tipo_movimento,
                            quantidade,
                            estoque_anterior,
                            estoque_posterior,
                            observacao
                        )
                        VALUES (%s, %s, %s, 'Saida', %s, %s, %s, %s);
                        """,
                        [
                            item['id_produto'],
                            usuario_id,
                            item_salvo['id_item'],
                            item['quantidade'],
                            estoque_anterior,
                            estoque_posterior,
                            f'Venda consumo #{venda["id_venda"]}',
                        ]
                    )

            cursor.execute(
                """
                UPDATE conta_consumo
                SET total_acumulado = total_acumulado + %s
                WHERE id_conta = %s
                RETURNING total_acumulado::float AS total_acumulado;
                """,
                [total_venda, conta['id_conta']]
            )
            conta_atualizada = dictfetchall(cursor)[0]

        venda['itens'] = itens_response
        venda['total_acumulado_conta'] = conta_atualizada['total_acumulado']
        return success_response(venda, 'VENDA_CREATED', 201)
    except Exception as e:
        return error_response(str(e), 'SERVER_ERROR', 500)


@csrf_exempt
@token_required
@require_http_methods(["GET"])
def consumo_conta_detail_view(request, conta_id):
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    cc.id_conta,
                    cc.fk_reserva,
                    cc.total_acumulado::float AS total_acumulado,
                    cc.status_conta,
                    cc.dt_abertura,
                    cc.dt_fechamento,
                    r.status_reserva,
                    h.id_hospede,
                    h.nome_hospede,
                    q.id_quarto,
                    q.numero AS numero_quarto
                FROM conta_consumo cc
                JOIN reserva r ON r.id_reserva = cc.fk_reserva
                LEFT JOIN hospede h ON h.id_hospede = r.fk_hospede_titular
                LEFT JOIN LATERAL (
                    SELECT rq_inner.fk_quarto AS id_quarto
                    FROM reserva_quarto rq_inner
                    WHERE rq_inner.fk_reserva = r.id_reserva
                    ORDER BY rq_inner.checkin DESC
                    LIMIT 1
                ) rq ON TRUE
                LEFT JOIN quarto q ON q.id_quarto = rq.id_quarto
                WHERE cc.id_conta = %s;
                """,
                [conta_id]
            )
            conta = dictfetchall(cursor)
            if not conta:
                return error_response('Conta de consumo nao encontrada.', 'NOT_FOUND', 404)

            cursor.execute(
                """
                SELECT
                    id_venda,
                    origem,
                    status_venda,
                    observacao,
                    total_venda::float AS total_venda,
                    dt_criacao,
                    dt_cancelamento
                FROM venda_consumo
                WHERE fk_conta = %s
                ORDER BY dt_criacao DESC;
                """,
                [conta_id]
            )
            vendas = dictfetchall(cursor)

            cursor.execute(
                """
                SELECT
                    i.id_item,
                    i.fk_venda,
                    i.fk_produto,
                    p.nome_produto,
                    c.nome_categoria,
                    c.tipo_categoria,
                    i.quantidade,
                    i.valor_unitario::float AS valor_unitario,
                    i.subtotal::float AS subtotal,
                    i.observacao,
                    i.dt_criacao
                FROM item_venda_consumo i
                JOIN venda_consumo v ON v.id_venda = i.fk_venda
                JOIN produto p ON p.id_produto = i.fk_produto
                JOIN categoria_produto c ON c.id_categoria = p.fk_categoria
                WHERE v.fk_conta = %s
                ORDER BY i.dt_criacao ASC;
                """,
                [conta_id]
            )
            itens = dictfetchall(cursor)
            ordens_lavanderia = _buscar_ordens_lavanderia_por_conta(cursor, conta_id)

        itens_por_venda = {}
        for item in itens:
            itens_por_venda.setdefault(item['fk_venda'], []).append(item)

        for venda in vendas:
            venda['itens'] = itens_por_venda.get(venda['id_venda'], [])

        response = conta[0]
        response['vendas'] = vendas
        response['ordens_lavanderia'] = ordens_lavanderia
        return success_response(response)
    except Exception as e:
        return error_response(str(e), 'SERVER_ERROR', 500)


@csrf_exempt
@token_required
@transaction.atomic
@require_http_methods(["POST"])
def consumo_fechar_conta_view(request, conta_id):
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE conta_consumo
                SET status_conta = 'Fechada', dt_fechamento = NOW()
                WHERE id_conta = %s
                  AND status_conta = 'Aberta'
                RETURNING
                    id_conta,
                    fk_reserva,
                    total_acumulado::float AS total_acumulado,
                    status_conta,
                    dt_fechamento;
                """,
                [conta_id]
            )
            conta = dictfetchall(cursor)

        if not conta:
            return error_response('Conta nao encontrada ou ja fechada.', 'CONTA_NAO_ABERTA', 409)

        return success_response(conta[0], 'CONTA_FECHADA')
    except Exception as e:
        return error_response(str(e), 'SERVER_ERROR', 500)



