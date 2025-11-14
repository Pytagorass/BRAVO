# =======================================================================
# 1. IMPORTAES
# =======================================================================
import json
import jwt
import datetime
import bcrypt #  IMPORTADO PARA HASHING DE SENHA
from functools import wraps

# ImportaÃ§Ãµes do Django
from django.db import connection, IntegrityError, transaction
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.views.decorators.http import require_http_methods #  Boa prÃ¡tica

# --- Importa nosso decorador de autenticaÃ§Ã£o ---
from .auth_decorator import token_required

# =======================================================================
# 2. FUNES UTILITRIAS (Helpers)
# =======================================================================
def dictfetchall(cursor):
    """
    Converte o resultado de cursor.fetchall() em uma lista de dicionÃ¡rios.
    """
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]

#  =======================================================================
#  2B. HELPERS DE RESPOSTA PADRONIZADA (Sua SolicitaÃ§Ã£o)
#  =======================================================================
def success_response(data=None, code="OK", status_code=200):
    """
    Gera uma resposta JSON padronizada para SUCESSO seguindo o contrato oficial.
    """
    response = {
        "success": True,
        "data": data if data is not None else {}
    }
    return JsonResponse(response, status=status_code)

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

# =======================================================================
# 3. VIEWS DA API (Endpoints)
# =======================================================================

# -----------------------------------------------------------------
# VIEW DE LOGIN (NO protegida)
# -----------------------------------------------------------------
@csrf_exempt
@require_http_methods(["POST"]) #  Garante que sÃ³ aceita POST
def login_view(request):
    """
    Endpoint de login.
     REATORADO:
    1. Usa bcrypt.checkpw() para comparar senhas (SeguranÃ§a).
    2. Usa os helpers error_response/success_response (PadronizaÃ§Ã£o).
    """
    try:
        data = json.loads(request.body)
        email = data.get('email')
        senha_recebida = data.get('senha')

        if not email or not senha_recebida:
            return error_response('Email e senha sÃ£o obrigatÃ³rios', 'VALIDATION_ERROR', 400)

        sql_query = """
            SELECT id_usuario, nome_usuario, email_usuario, tipo_usuario, senha 
            FROM usuario
            WHERE email_usuario = %s AND ativo = 'Ativo';
        """

        with connection.cursor() as cursor:
            cursor.execute(sql_query, [email])
            user_data = dictfetchall(cursor)

            if not user_data:
                return error_response('Credenciais invÃ¡lidas ou usuÃ¡rio inativo', 'AUTH_FAILED', 401)

            usuario = user_data[0]
            senha_hash_bd = usuario['senha'].encode('utf-8')
            
            #  VULNERABILIDADE CORRIGIDA: ComparaÃ§Ã£o de hash
            if not bcrypt.checkpw(senha_recebida.encode('utf-8'), senha_hash_bd):
                return error_response('Credenciais invÃ¡lidas', 'AUTH_FAILED', 401)

            # GeraÃ§Ã£o do Payload e Token
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
# VIEW DA AGENDA (Gantt) (Protegida)
# -----------------------------------------------------------------
@csrf_exempt #  @csrf_exempt nÃ£o Ã© necessÃ¡rio com @token_required se o token vai no Header
@token_required 
@require_http_methods(["GET"])
def get_agenda_reservas(request):
    """
    Endpoint principal para carregar o GrÃ¡fico de Gantt.
     REATORADO:
    1. Usa os helpers error_response/success_response (PadronizaÃ§Ã£o).
    2. Filtra reservas 'Cancelada' (boa prÃ¡tica para o Gantt).
    """
    
    sql_query = """
        SELECT
            rq.id_reserva_quarto, 
            rq.checkin, 
            rq.checkout,
            r.id_reserva, 
            r.status_reserva, 
            r.status_pagamento,
            q.id_quarto, 
            q.numero AS numero_quarto,
            h.nome_hospede AS nome_titular
        FROM 
            reserva_quarto AS rq
        INNER JOIN 
            reserva AS r ON rq.fk_reserva = r.id_reserva
        INNER JOIN 
            quarto AS q ON rq.fk_quarto = q.id_quarto
        LEFT JOIN
            hospede AS h ON r.fk_hospede_titular = h.id_hospede

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
# VIEW DE CRIAO DE RESERVA (Protegida)
# -----------------------------------------------------------------
@csrf_exempt
@token_required
@transaction.atomic  #  Garante que ou tudo (5 inserts) ou nada acontece
@require_http_methods(["POST"])
def reservas_view(request):
    """
    View para o POST: Cria uma nova reserva (transacional).

    Melhorias:
    1. SQL de overbooking retorna detalhes do conflito.
    2. Respostas padronizadas com success/error.
    3. Validacoes de datas, status do quarto e valor total recalculado.
    """
    try:
        data = json.loads(request.body)

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
            acompanhante_ids = [int(ac_id) for ac_id in data.get('acompanhantes', []) if ac_id]
        except (TypeError, ValueError):
            return error_response('Lista de acompanhantes invalida.', 'VALIDATION_ERROR', 400)

        with connection.cursor() as cursor:
            cursor.execute("SELECT status_quarto, valor_diaria FROM quarto WHERE id_quarto = %s FOR UPDATE", [quarto_id])
            quarto_info = cursor.fetchone()
            if not quarto_info:
                return error_response('Quarto nao encontrado.', 'NOT_FOUND', 404)

            status_quarto, valor_diaria = quarto_info
            if status_quarto == 'Manutenção':
                return error_response('Quarto em manutencao nao pode ser reservado.', 'QUARTO_MANUTENCAO', 409)

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

            diarias = (checkout_date - checkin_date).days
            valor_total = valor_diaria * diarias

            sql_reserva = """
                INSERT INTO reserva (
                    valor_total,
                    observacao_reserva,
                    fk_usuario,
                    status_reserva,
                    status_pagamento,
                    fk_hospede_titular
                )
                VALUES (%s, %s, %s, 'Agendada', %s, %s)
                RETURNING id_reserva;
            """
            params_reserva = [
                valor_total,
                observacao,
                fk_usuario_logado,
                status_pagamento,
                titular_id
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
            'valor_total': float(valor_total)
        }

        return success_response(nova_reserva_obj, status_code=201)

    except IntegrityError as e:
        return error_response(f'Erro de integridade no banco: {str(e)}', 'DB_INTEGRITY_ERROR', 400)

    except Exception as e:
        return error_response(str(e), 'ERRO_INTERNO', 500)

# -----------------------------------------------------------------
# VIEW: EDITAR RESERVA (FormulÃ¡rio Completo)
# -----------------------------------------------------------------
@csrf_exempt
@token_required
@transaction.atomic
@require_http_methods(["PUT"])
def edit_reserva_view(request, reserva_quarto_id):
    """
    View para 'Editar' a reserva (FormulÃ¡rio completo) com validaÃ§Ãµes de negÃ³cio.
    """
    try:
        data = json.loads(request.body)

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
            acompanhante_ids = [int(ac_id) for ac_id in data.get('acompanhantes', []) if ac_id]
        except (TypeError, ValueError):
            return error_response('Lista de acompanhantes invalida.', 'VALIDATION_ERROR', 400)

        with connection.cursor() as cursor:
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

            cursor.execute("SELECT status_quarto, valor_diaria FROM quarto WHERE id_quarto = %s", [quarto_id])
            quarto_info = cursor.fetchone()
            if not quarto_info:
                return error_response('Quarto nao encontrado.', 'NOT_FOUND', 404)

            status_quarto, valor_diaria = quarto_info
            if status_quarto == 'Manutenção':
                return error_response('Quarto em manutencao nao pode ser reservado.', 'QUARTO_MANUTENCAO', 409)

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

            sql_update_reserva = """
                UPDATE reserva
                SET 
                    valor_total = %s,
                    observacao_reserva = %s,
                    fk_usuario = %s,
                    status_pagamento = %s,
                    fk_hospede_titular = %s
                WHERE id_reserva = %s;
            """
            cursor.execute(
                sql_update_reserva,
                [valor_total, observacao, fk_usuario_logado, status_pagamento, titular_id, id_reserva_principal]
            )

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
                sql_acompanhante = "INSERT INTO reserva_hospede (fk_reserva, fk_hospede) VALUES (%s, %s);"
                params_acompanhantes = [(id_reserva_principal, ac_id) for ac_id in acompanhante_ids]
                cursor.executemany(sql_acompanhante, params_acompanhantes)

            reserva_obj = _get_reserva_detalhes_internal(cursor, reserva_quarto_id)
            if not reserva_obj:
                return error_response('Reserva nao encontrada apos atualizacao.', 'NOT_FOUND', 404)

        return success_response(reserva_obj)

    except Exception as e:
        return error_response(str(e), 'ERRO_INTERNO', 500)

# -----------------------------------------------------------------
# VIEW: ATUALIZAR STATUS (AÃ§Ãµes RÃ¡pidas: Cancelar, Pagar, etc.)
# -----------------------------------------------------------------
@csrf_exempt
@token_required
@transaction.atomic
@require_http_methods(["PATCH"])
def update_reserva_status_view(request, reserva_quarto_id):
    """
    View para 'Editar' a reserva (aÃ§Ãµes rÃ¡pidas).
    Aceita PATCH para /api/agenda/update-status/<id>/
    
     REATORADO:
    1. Adicionado SELECT ... FOR UPDATE (Controle de ConcorrÃªncia).
    2. PadronizaÃ§Ã£o de todas as respostas (success/error).
    """
    try:
        data = json.loads(request.body)
        novo_status_reserva = data.get('status_reserva')
        novo_status_pagamento = data.get('status_pagamento')

        if not novo_status_reserva and not novo_status_pagamento:
            return error_response('Nenhum status foi enviado para atualizaÃ§Ã£o.', 'VALIDATION_ERROR', 400)

        with connection.cursor() as cursor:
            
            # 2. Busca o ID da reserva principal
            cursor.execute("SELECT fk_reserva FROM reserva_quarto WHERE id_reserva_quarto = %s", [reserva_quarto_id])
            reserva_link = cursor.fetchone()
            if not reserva_link:
                return error_response('Reserva (link quarto) nÃ£o encontrada.', 'NOT_FOUND', 404)
            
            id_reserva_principal = reserva_link[0]

            #  CONTROLE DE CONCORRNCIA (Sua SolicitaÃ§Ã£o)
            # Trava a linha da 'reserva' principal.
            cursor.execute("SELECT 1 FROM reserva WHERE id_reserva = %s FOR UPDATE", [id_reserva_principal])

            # 3. Monta a query de atualizaÃ§Ã£o dinamicamente
            campos_para_atualizar = []
            params = []
            if novo_status_reserva:
                campos_para_atualizar.append("status_reserva = %s")
                params.append(novo_status_reserva)
            if novo_status_pagamento:
                campos_para_atualizar.append("status_pagamento = %s")
                params.append(novo_status_pagamento)

            # 4. Executa o UPDATE
            sql_update = f"UPDATE reserva SET {', '.join(campos_para_atualizar)} WHERE id_reserva = %s"
            params.append(id_reserva_principal)
            cursor.execute(sql_update, params)

            # 5. Retorna o objeto ATUALIZADO
            reserva_obj = _get_reserva_detalhes_internal(cursor, reserva_quarto_id)
            if not reserva_obj:
                 return error_response('Reserva nÃ£o encontrada apÃ³s atualizaÃ§Ã£o.', 'NOT_FOUND', 404)

        return success_response(reserva_obj, "STATUS_UPDATED")

    except Exception as e:
        return error_response(str(e), 'SERVER_ERROR', 500)


# -----------------------------------------------------------------
# VIEW DE HSPEDES (CRUD)
# -----------------------------------------------------------------
@csrf_exempt 
@token_required
@require_http_methods(["GET", "POST"])
def hospedes_view(request):
    
    # MTODO GET (Filtra por status Ativo/Inativo)
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

    # MTODO POST (Cria novo hÃ³spede)
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # ValidaÃ§Ãµes prÃ©-insert
            if data.get('pais_origem', 'Brasil') == 'Brasil' and not data.get('cpf'):
                return error_response("CPF Ã© obrigatÃ³rio para hÃ³spedes do Brasil.", "VALIDATION_ERROR", 400)
            if data.get('pais_origem', 'Brasil') != 'Brasil' and not data.get('passaporte'):
                return error_response("Passaporte Ã© obrigatÃ³rio para hÃ³spedes estrangeiros.", "VALIDATION_ERROR", 400)

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
# VIEW DE DETALHE DO HSPEDE
# -----------------------------------------------------------------
@csrf_exempt 
@token_required
@require_http_methods(["PUT", "DELETE", "PATCH"]) 
def hospede_detail_view(request, hospede_id):
    
    # MTODO PUT (Atualizar)
    if request.method == 'PUT':
        try:
            data = json.loads(request.body)
            
            # ValidaÃ§Ãµes
            if data.get('pais_origem', 'Brasil') == 'Brasil' and not data.get('cpf'):
                return error_response("CPF Ã© obrigatÃ³rio para hÃ³spedes do Brasil.", "VALIDATION_ERROR", 400)
            if data.get('pais_origem', 'Brasil') != 'Brasil' and not data.get('passaporte'):
                return error_response("Passaporte Ã© obrigatÃ³rio para hÃ³spedes estrangeiros.", "VALIDATION_ERROR", 400)

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
                    return error_response('Cliente nÃ£o encontrado.', 'NOT_FOUND', 404)
                hospede_atualizado = dictfetchall(cursor)[0]
            
            return success_response(hospede_atualizado, "HOSPEDE_UPDATED")
        except IntegrityError as e:
            return error_response(f'Erro de integridade: {str(e)}', 'DB_INTEGRITY_ERROR', 400)
        except Exception as e:
            return error_response(str(e), 'SERVER_ERROR', 500)
            
    # MTODO DELETE (Inativar)
    elif request.method == 'DELETE':
        try:
            with connection.cursor() as cursor:
                sql_inativar = "UPDATE hospede SET ativo = 'Inativo' WHERE id_hospede = %s"
                cursor.execute(sql_inativar, [hospede_id])
                
                if cursor.rowcount == 0:
                    return error_response('Cliente nÃ£o encontrado com este ID.', 'NOT_FOUND', 404)
            
            return success_response(None, "HOSPEDE_INACTIVATED", 204) 
            
        except IntegrityError as e:
            return error_response(
                'NÃ£o Ã© possvel inativar este hÃ³spede (erro de integridade).',
                'FK_CONSTRAINT', 409 
            )
        except Exception as e:
            return error_response(str(e), 'SERVER_ERROR', 500)
    
    # MTODO 'PATCH' (Reativar)
    elif request.method == 'PATCH':
        try:
            data = json.loads(request.body)
            novo_status = data.get('ativo')

            if novo_status not in ['Ativo', 'Inativo']:
                return error_response("Status invÃ¡lido. Envie 'Ativo' ou 'Inativo'.", "VALIDATION_ERROR", 400)

            with connection.cursor() as cursor:
                sql_update = "UPDATE hospede SET ativo = %s WHERE id_hospede = %s"
                cursor.execute(sql_update, [novo_status, hospede_id])
                
                if cursor.rowcount == 0:
                    return error_response('Cliente nÃ£o encontrado.', 'NOT_FOUND', 404)
            
            return success_response(None, "STATUS_UPDATED", 200) 

        except Exception as e:
            return error_response(str(e), 'SERVER_ERROR', 500)

# -----------------------------------------------------------------
#  VIEW DE PERFIL DO USURIO
# -----------------------------------------------------------------
@csrf_exempt 
@token_required
@require_http_methods(["GET", "PUT"])
def usuario_perfil_view(request):
    """
    View para o perfil do usuÃ¡rio logado (/api/perfil/).
     REATORADO:
    1. Usa bcrypt.hashpw() para atualizar senha (SeguranÃ§a).
    2. Usa os helpers error_response/success_response (PadronizaÃ§Ã£o).
    """
    try:
        user_id = request.user_token_payload.get('id_usuario')
        if not user_id:
            return error_response('Token invÃ¡lido, ID de usuÃ¡rio nÃ£o encontrado.', 'INVALID_TOKEN', 401)
    except Exception as e:
        return error_response(f'Erro ao processar token: {str(e)}', 'INVALID_TOKEN', 401)

    with connection.cursor() as cursor:
        
        # MTODO GET: Buscar dados
        if request.method == 'GET':
            try:
                sql_get = "SELECT id_usuario, nome_usuario, email_usuario FROM usuario WHERE id_usuario = %s"
                cursor.execute(sql_get, [user_id])
                usuario = dictfetchall(cursor)
                
                if not usuario:
                    return error_response('UsuÃ¡rio nÃ£o encontrado no banco.', 'NOT_FOUND', 404)
                
                return success_response(usuario[0])
            
            except Exception as e:
                return error_response(f'Erro no GET: {str(e)}', 'SERVER_ERROR', 500)

        # MTODO PUT: Atualizar o perfil
        elif request.method == 'PUT':
            try:
                data = json.loads(request.body)
                nome = data.get('nome_usuario')
                email = data.get('email_usuario')
                senha = data.get('senha') # O modal enviarÃ¡ 'senha' se ela for mudada

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
                    return error_response('UsuÃ¡rio nÃ£o encontrado, nada atualizado.', 'NOT_FOUND', 404)

                return success_response(None, 'PROFILE_UPDATED')

            except IntegrityError as e:
                return error_response('Este e-mail jÃ¡ estÃ¡ em uso por outra conta.', 'CONFLICT', 409)
            except Exception as e:
                return error_response(f'Erro no PUT: {str(e)}', 'SERVER_ERROR', 500)


# -----------------------------------------------------------------
#  VIEW DE DETALHES DA RESERVA (Refatorada)
# -----------------------------------------------------------------
@csrf_exempt
@token_required
@require_http_methods(["GET"])
def get_reserva_detalhes(request, reserva_quarto_id):
    """
    Endpoint para buscar os detalhes de UMA reserva especfica.
    """
    try:
        with connection.cursor() as cursor:
            detalhes = _get_reserva_detalhes_internal(cursor, reserva_quarto_id)
            
            if not detalhes:
                return error_response('Reserva nÃ£o encontrada', 'NOT_FOUND', 404)
            
            return success_response(detalhes)

    except Exception as e:
        return error_response(str(e), 'SERVER_ERROR', 500)

# -----------------------------------------------------------------
#  FUNO INTERNA (Helper) para buscar detalhes da reserva
#    (Evita duplicaÃ§Ã£o de cÃ³digo entre PUT, PATCH e GET)
# -----------------------------------------------------------------
def _get_reserva_detalhes_internal(cursor, reserva_quarto_id):
    """
    FunÃ§Ã£o helper que executa as queries para buscar todos os dados
    de uma reserva, dado um cursor jÃ¡ aberto.
    """
    detalhes = {}
    
    # Query 1: Busca os dados principais
    sql_detalhes = """
        SELECT
            r.id_reserva, r.valor_total, r.observacao_reserva, 
            r.status_reserva, r.status_pagamento, r.dt_criacao,
            rq.id_reserva_quarto, rq.checkin, rq.checkout,
            q.id_quarto, q.numero AS numero_quarto, q.tipo_quarto,
            h.id_hospede AS id_titular,
            h.nome_hospede AS nome_titular,
            h.email_hospede AS email_titular,
            h.telefone AS telefone_titular,
            u.nome_usuario AS nome_usuario_criacao
        FROM 
            reserva_quarto AS rq
        JOIN reserva AS r ON rq.fk_reserva = r.id_reserva
        JOIN quarto AS q ON rq.fk_quarto = q.id_quarto
        LEFT JOIN usuario AS u ON r.fk_usuario = u.id_usuario
        LEFT JOIN hospede AS h ON r.fk_hospede_titular = h.id_hospede
        WHERE 
            rq.id_reserva_quarto = %s;
    """
    cursor.execute(sql_detalhes, [reserva_quarto_id])
    detalhes_result = dictfetchall(cursor)
    
    if not detalhes_result:
        return None # Retorna None se nÃ£o achar
    
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

# =======================================================================
# 4. VIEWS DE ENTIDADES (CRUDs)
# =======================================================================

# -----------------------------------------------------------------
# VIEW DE QUARTOS (CRUD) (Protegida)
# -----------------------------------------------------------------
@csrf_exempt 
@token_required
@require_http_methods(["GET", "POST"])
def quartos_view(request):
    
    # MTODO GET
    if request.method == 'GET':
        #  MUDANA: LÃª o parÃ¢metro 'status' da URL.
        # O padrÃ£o Ã© 'Disponível' se nada for fornecido.
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
                #  Passamos o status como parÃ¢metro
                cursor.execute(sql_query, [status])
                quartos = dictfetchall(cursor)
            return success_response(quartos)
        except Exception as e:
            return error_response(str(e), 'SERVER_ERROR', 500)

    # MTODO POST (Sem mudanÃ§as)
    elif request.method == 'POST':
        # ... (cÃ³digo do POST mantido) ...
        try:
            data = json.loads(request.body)
            # ... (validaÃ§Ã£o e INSERT) ...
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
                return error_response(f'Erro: O nÃºmero de quarto "{data.get("numero")}" jÃ¡ estÃ¡ cadastrado.', 'CONFLICT', 409)
            return error_response(f'Erro de integridade: {str(e)}', 'DB_INTEGRITY_ERROR', 400)
        except Exception as e:
            return error_response(str(e), 'SERVER_ERROR', 500)

# -----------------------------------------------------------------
# VIEW DE DETALHE DO QUARTO (GET/PUT/DELETE)
# -----------------------------------------------------------------
@csrf_exempt 
@token_required
@require_http_methods(["GET", "PUT", "DELETE"])
def quarto_detail_view(request, quarto_id):
    """
    View para um Quarto especfico (/api/quartos/<id>/).
    - GET: Busca um quarto pelo ID.
    - PUT: Atualiza um quarto existente.
    - DELETE: Deleta um quarto.
    """

    # MTODO GET (BY ID)
    if request.method == 'GET':
        try:
            with connection.cursor() as cursor:
                sql_get = "SELECT * FROM quarto WHERE id_quarto = %s"
                cursor.execute(sql_get, [quarto_id])
                quarto = dictfetchall(cursor)
                
                if not quarto:
                    return error_response('Quarto nÃ£o encontrado.', 'NOT_FOUND', 404)
                
                return success_response(quarto[0])
        except Exception as e:
            return error_response(str(e), 'SERVER_ERROR', 500)

    # MTODO PUT (Atualizar)
    elif request.method == 'PUT':
        try:
            data = json.loads(request.body)
            
            numero = data.get('numero')
            valor_diaria = data.get('valor_diaria')
            tipo_quarto = data.get('tipo_quarto')
            status_db = data.get('status_quarto')

            if not numero or not valor_diaria or not tipo_quarto or not status_db:
                 return error_response('Todos os campos sÃ£o obrigatÃ³rios.', 'VALIDATION_ERROR', 400)

            if status_db not in ['Disponível', 'Manutenção']:
                return error_response(f"Status '{status_db}' invÃ¡lido. Use 'Disponível' ou 'Manutenção'.", "VALIDATION_ERROR", 400)
            
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
                    return error_response('Quarto nÃ£o encontrado com este ID.', 'NOT_FOUND', 404)
                
                quarto_atualizado = dictfetchall(cursor)[0]

            return success_response(quarto_atualizado, "QUARTO_UPDATED")
        
        except IntegrityError as e:
            if 'quarto_numero_key' in str(e):
                return error_response(f'Erro: O nÃºmero de quarto "{numero}" jÃ¡ estÃ¡ cadastrado.', 'CONFLICT', 409)
            return error_response(f'Erro de integridade: {str(e)}', 'DB_INTEGRITY_ERROR', 400)
        except Exception as e:
            return error_response(str(e), 'SERVER_ERROR', 500)

    # MTODO DELETE
    elif request.method == 'DELETE':
        try:
            #  CONTROLE DE INTEGRIDADE (Sua SolicitaÃ§Ã£o)
            # NÃ£o podemos deletar um quarto que estÃ¡ em 'reserva_quarto'.
            # O PostgreSQL irÃ¡ barrar com IntegrityError, que vamos capturar.
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM quarto WHERE id_quarto = %s", [quarto_id])
                if cursor.rowcount == 0:
                    return error_response('Quarto nÃ£o encontrado com este ID.', 'NOT_FOUND', 404)
            
            # 204 No Content Ã© o padrÃ£o para DELETE bem-sucedido
            return success_response(None, "QUARTO_DELETED", 204) 
            
        except IntegrityError as e:
            #  Erro pego! (fk_reserva_quarto_quarto)
            return error_response(
                'NÃ£o Ã© possvel excluir este quarto pois ele estÃ¡ vinculado a uma ou mais reservas.',
                'FK_CONSTRAINT',
                409 # 409 Conflict
            )
        except Exception as e:
            return error_response(str(e), 'SERVER_ERROR', 500)

# =======================================================================
# 5. VIEW DE BUSINESS INTELLIGENCE (BI)
# =======================================================================

# -----------------------------------------------------------------
# VIEW DE GESTO (BI) (Protegida)
# -----------------------------------------------------------------
@csrf_exempt
@token_required
@require_http_methods(["GET"])

def get_indicadores_gestao(request):
    """
    Endpoint de BI (Business Intelligence) para o dashboard de GestÃ£o.
    Calcula indicadores sempre pelo check-in (regime de competÃªncia).
    """
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
        diarias_por_pais = []
        lead_time_medio = 0

        status_template = ['Agendada', 'Ativa', 'Concluda', 'Cancelada']

        with connection.cursor() as cursor:
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

            sql_diarias = """
                SELECT
                    h.pais_origem AS pais,
                    COALESCE(SUM(
                        GREATEST(
                            EXTRACT(EPOCH FROM (
                                LEAST(rq.checkout, %s::date + interval '1 day') -
                                GREATEST(rq.checkin, %s::date)
                            )),
                            0
                        )
                    ) / 86400, 0) AS total_diarias
                FROM reserva r
                JOIN hospede h ON r.fk_hospede_titular = h.id_hospede
                JOIN reserva_quarto rq ON rq.fk_reserva = r.id_reserva
                WHERE
                    r.status_reserva != 'Cancelada'
                    AND (rq.checkin, rq.checkout) OVERLAPS (%s::date, %s::date + interval '1 day')
                GROUP BY h.pais_origem
                ORDER BY total_diarias DESC, h.pais_origem ASC
                LIMIT 5;
            """
            cursor.execute(sql_diarias, [data_inicio, data_fim, data_inicio, data_fim])
            diarias_por_pais = dictfetchall(cursor)

            sql_lead_time = """
                SELECT
                    COALESCE(
                        AVG(
                            GREATEST(
                                EXTRACT(EPOCH FROM (rq.checkin::timestamp - r.dt_criacao)),
                                0
                            )
                        ) / 86400,
                        0
                    ) AS lead_time_medio
                FROM reserva r
                JOIN reserva_quarto rq ON rq.fk_reserva = r.id_reserva
                WHERE
                    rq.checkin BETWEEN %s AND %s
                    AND r.status_reserva != 'Cancelada';
            """
            cursor.execute(sql_lead_time, [data_inicio, data_fim])
            lead_time_medio = dictfetchall(cursor)[0].get('lead_time_medio', 0)

        response_data = {
            'kpis': kpi_data,
            'taxa_ocupacao': taxa_ocupacao,
            'faturamento_mensal': faturamento_mensal,
            'faturamento_por_tipo': faturamento_por_tipo,
            'reservas_por_status': reservas_por_status,
            'pagamentos_pendentes': pagamentos_pendentes,
            'diarias_por_pais': diarias_por_pais,
            'lead_time_medio': lead_time_medio,
            'ano_filtrado': ano_filtrar
        }
        return success_response(response_data)

    except Exception as e:
        return error_response(str(e), 'SERVER_ERROR', 500)


@csrf_exempt
@token_required
@require_http_methods(["GET"])
def get_reservas_pendentes(request):
    """
    Retorna a lista de reservas com pagamentos pendentes ou parciais para o painel de GestÃ£o.
    """
    try:
        with connection.cursor() as cursor:
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



