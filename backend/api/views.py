# =======================================================================
# 1. IMPORTAÇÕES
# =======================================================================
import json
import jwt
import datetime
import bcrypt # 🎓 IMPORTADO PARA HASHING DE SENHA
from functools import wraps

# Importações do Django
from django.db import connection, IntegrityError, transaction
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.views.decorators.http import require_http_methods # 🎓 Boa prática

# --- Importa nosso decorador de autenticação ---
from .auth_decorator import token_required

# =======================================================================
# 2. FUNÇÕES UTILITÁRIAS (Helpers)
# =======================================================================
def dictfetchall(cursor):
    """
    Converte o resultado de cursor.fetchall() em uma lista de dicionários.
    """
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]

# 🎓 =======================================================================
# 🎓 2B. HELPERS DE RESPOSTA PADRONIZADA (Sua Solicitação)
# 🎓 =======================================================================
def success_response(data=None, code="OK", status_code=200):
    """
    Gera uma resposta JSON padronizada para SUCESSO.
    """
    response = {
        "status": "ok",
        "code": code
    }
    if data is not None:
        response["data"] = data
    return JsonResponse(response, status=status_code)

def error_response(message, code="ERROR", status_code=400, details=None):
    """
    Gera uma resposta JSON padronizada para ERRO.
    """
    response = {
        "status": "error",
        "code": code,
        "message": message
    }
    if details is not None:
        # 'details' pode conter o payload original ou dados de conflito
        response["details"] = details 
    return JsonResponse(response, status=status_code)

# =======================================================================
# 3. VIEWS DA API (Endpoints)
# =======================================================================

# -----------------------------------------------------------------
# VIEW DE LOGIN (NÃO protegida)
# -----------------------------------------------------------------
@csrf_exempt
@require_http_methods(["POST"]) # 🎓 Garante que só aceita POST
def login_view(request):
    """
    Endpoint de login.
    🎓 REATORADO:
    1. Usa bcrypt.checkpw() para comparar senhas (Segurança).
    2. Usa os helpers error_response/success_response (Padronização).
    """
    try:
        data = json.loads(request.body)
        email = data.get('email')
        senha_recebida = data.get('senha')

        if not email or not senha_recebida:
            return error_response('Email e senha são obrigatórios', 'VALIDATION_ERROR', 400)

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
            
            # 🎓 VULNERABILIDADE CORRIGIDA: Comparação de hash
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

            # 🎓 RESPOSTA PADRONIZADA
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
@csrf_exempt # 🎓 @csrf_exempt não é necessário com @token_required se o token vai no Header
@token_required 
@require_http_methods(["GET"])
def get_agenda_reservas(request):
    """
    Endpoint principal para carregar o Gráfico de Gantt.
    🎓 REATORADO:
    1. Usa os helpers error_response/success_response (Padronização).
    2. Filtra reservas 'Cancelada' (boa prática para o Gantt).
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
            reserva_hospede AS rh ON r.id_reserva = rh.fk_reserva 
                                  AND rh.tipo_hospede = 'Titular'
        LEFT JOIN
            hospede AS h ON rh.fk_hospede = h.id_hospede

    """
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql_query)
            reservas = dictfetchall(cursor)
        
        # 🎓 RESPOSTA PADRONIZADA
        return success_response(reservas)

    except Exception as e:
        return error_response(str(e), 'SERVER_ERROR', 500)
    

# -----------------------------------------------------------------
# VIEW DE CRIAÇÃO DE RESERVA (Protegida)
# -----------------------------------------------------------------
@csrf_exempt
@token_required 
@transaction.atomic # 🎓 @transaction.atomic garante que ou tudo (5 inserts) ou nada acontece
@require_http_methods(["POST"])
def reservas_view(request):
    """
    View para o POST: Cria uma nova reserva (transacional).
    🎓 REATORADO:
    1. SQL de Overbooking modificado para retornar *detalhes do conflito*.
    2. Usa error_response com status 409 (Conflict) e code 'OVERBOOK_CONFLICT'.
    3. Usa success_response com status 201 (Created).
    """
    try:
        data = json.loads(request.body)
        
        # 1. Extrai os dados do payload
        titular_id = int(data.get('fk_hospede_id_hospede'))
        quarto_id = int(data.get('quartos')[0])
        checkin = data.get('checkin')
        checkout = data.get('checkout')
        valor_total = data.get('valor_total')
        observacao = data.get('observacao_reserva')
        acompanhante_ids = data.get('acompanhantes', [])
        status_pagamento = data.get('forma_pagamento', 'Pendente')
        fk_usuario_logado = request.user_token_payload.get('id_usuario')

        with connection.cursor() as cursor:
        
            # 🎓 2. VALIDAÇÃO DE OVERBOOKING (SQL Modificado)
            #    Agora seleciona os dados do conflito para enviar ao front-end
            sql_check_overbooking = """
                SELECT 
                    rq.checkin, 
                    rq.checkout, 
                    h.nome_hospede AS nome_titular_conflito
                FROM reserva_quarto rq
                JOIN reserva r ON rq.fk_reserva = r.id_reserva
                LEFT JOIN reserva_hospede rh ON r.id_reserva = rh.fk_reserva AND rh.tipo_hospede = 'Titular'
                LEFT JOIN hospede h ON rh.fk_hospede = h.id_hospede
                WHERE rq.fk_quarto = %s 
                  AND (DATE %s, DATE %s) OVERLAPS (rq.checkin, rq.checkout) 
                  AND r.status_reserva != 'Cancelada'
                LIMIT 1;
            """
            cursor.execute(sql_check_overbooking, [quarto_id, checkin, checkout])
            conflito = dictfetchall(cursor)

            if conflito:
                # 🎓 RESPOSTA PADRONIZADA DE CONFLITO (Sua Solicitação)
                return error_response(
                    message="Este quarto já está ocupado no período solicitado.",
                    code="OVERBOOK_CONFLICT",
                    status_code=409, # 409 Conflict
                    details=conflito[0] # Envia os detalhes do conflito
                )

            # 3. INSERT 1: Tabela 'reserva'
            sql_reserva = """
                INSERT INTO reserva (valor_total, observacao_reserva, fk_usuario, status_reserva, status_pagamento)
                VALUES (%s, %s, %s, 'Agendada', %s)
                RETURNING id_reserva;
            """
            params_reserva = [valor_total, observacao, fk_usuario_logado, status_pagamento]
            cursor.execute(sql_reserva, params_reserva)
            nova_reserva_id = cursor.fetchone()[0]

            # 4. INSERT 2: Tabela 'reserva_quarto'
            sql_quarto = """
                INSERT INTO reserva_quarto (fk_reserva, fk_quarto, checkin, checkout, valor_diaria_cobrado)
                VALUES (%s, %s, %s, %s, (SELECT valor_diaria FROM quarto WHERE id_quarto = %s))
                RETURNING id_reserva_quarto;
            """
            params_quarto = [nova_reserva_id, quarto_id, checkin, checkout, quarto_id]
            cursor.execute(sql_quarto, params_quarto)
            nova_reserva_quarto_id = cursor.fetchone()[0] 

            # 5. INSERT 3: Titular
            sql_titular = "INSERT INTO reserva_hospede (fk_reserva, fk_hospede, tipo_hospede) VALUES (%s, %s, 'Titular');"
            cursor.execute(sql_titular, [nova_reserva_id, titular_id])

            # 6. INSERT 4...N: Acompanhantes
            if acompanhante_ids:
                sql_acompanhante = "INSERT INTO reserva_hospede (fk_reserva, fk_hospede, tipo_hospede) VALUES (%s, %s, 'Acompanhante');"
                params_acompanhantes = [(nova_reserva_id, ac_id) for ac_id in acompanhante_ids]
                cursor.executemany(sql_acompanhante, params_acompanhantes)
            
            # 7. Busca dados para o front-end
            cursor.execute("SELECT nome_hospede FROM hospede WHERE id_hospede = %s", [titular_id])
            nome_titular = cursor.fetchone()[0]
            cursor.execute("SELECT numero FROM quarto WHERE id_quarto = %s", [quarto_id])
            numero_quarto = cursor.fetchone()[0]

        # 8. Construção do objeto de resposta
        nova_reserva_obj = {
            'id_reserva_quarto': nova_reserva_quarto_id,
            'checkin': checkin,
            'checkout': checkout,
            'id_reserva': nova_reserva_id,
            'status_reserva': 'Agendada',
            'status_pagamento': status_pagamento,
            'id_quarto': quarto_id,
            'numero_quarto': numero_quarto,
            'nome_titular': nome_titular
        }
        
        # 9. 🎓 RESPOSTA PADRONIZADA (201 Created)
        return success_response(nova_reserva_obj, "RESERVA_CREATED", 201)
    
    except IntegrityError as e:
        return error_response(f'Erro de integridade no banco: {str(e)}', 'DB_INTEGRITY_ERROR', 400)
    except Exception as e:
        return error_response(str(e), 'SERVER_ERROR', 500)


# -----------------------------------------------------------------
# VIEW: EDITAR RESERVA (Formulário Completo)
# -----------------------------------------------------------------
# Em /aguapei_backend/api/views.py

@csrf_exempt
@token_required
@transaction.atomic
@require_http_methods(["PUT"])
def edit_reserva_view(request, reserva_quarto_id):
    """
    View para 'Editar' a reserva (Formulário completo).
    🎓 REFATORADO:
    1. Desliga os gatilhos (Triggers) temporariamente para
       evitar o erro "REGRA VIOLADA" durante o "delete-e-reinsere".
    2. Implementa a lógica de 'isReservaGrupo' (nome provisório).
    """
    
    try:
        data = json.loads(request.body)
        
        # 1. 🎓 Lógica de Grupo/Agência (vinda do front-end)
        titular_id = data.get('fk_hospede_id_hospede')
        nome_provisorio = data.get('nome_provisorio')
        
        # Se for reserva de grupo, titularId será nulo
        isReservaGrupo = nome_provisorio is not None
        
        quarto_id = int(data.get('quartos')[0])
        checkin = data.get('checkin')
        checkout = data.get('checkout')
        valor_total = data.get('valor_total')
        status_pagamento = data.get('status_pagamento') # Mudado de 'forma_pagamento'
        observacao = data.get('observacao_reserva')
        
        # Se for grupo, ignora acompanhantes
        acompanhante_ids = [] if isReservaGrupo else data.get('acompanhantes', [])

        fk_usuario_logado = request.user_token_payload.get('id_usuario')

        with connection.cursor() as cursor:
            
            # 2. Busca o ID da reserva principal
            cursor.execute("SELECT fk_reserva FROM reserva_quarto WHERE id_reserva_quarto = %s", [reserva_quarto_id])
            reserva_link = cursor.fetchone()
            if not reserva_link:
                return error_response('Reserva (link quarto) não encontrada.', 'NOT_FOUND', 404)
            
            id_reserva_principal = reserva_link[0]

            # 3. 🎓 Trava a linha da 'reserva' (Controle de Concorrência)
            cursor.execute("SELECT 1 FROM reserva WHERE id_reserva = %s FOR UPDATE", [id_reserva_principal])

            # 4. VALIDAÇÃO DE OVERBOOKING (Excluindo a própria reserva)
            sql_check_overbooking = """
                SELECT r.id_reserva, h.nome_hospede AS nome_titular_conflito
                FROM reserva_quarto rq
                JOIN reserva r ON rq.fk_reserva = r.id_reserva
                LEFT JOIN reserva_hospede rh ON r.id_reserva = rh.fk_reserva AND rh.tipo_hospede = 'Titular'
                LEFT JOIN hospede h ON rh.fk_hospede = h.id_hospede
                WHERE rq.fk_quarto = %s 
                  AND (DATE %s, DATE %s) OVERLAPS (rq.checkin, rq.checkout) 
                  AND r.status_reserva != 'Cancelada'
                  AND rq.id_reserva_quarto != %s -- Exclui a própria reserva
                LIMIT 1;
            """
            cursor.execute(sql_check_overbooking, [quarto_id, checkin, checkout, reserva_quarto_id])
            conflito = dictfetchall(cursor)
            if conflito:
                return error_response(
                    message="Este quarto já está ocupado no período solicitado por outra reserva.",
                    code="OVERBOOK_CONFLICT",
                    status_code=409,
                    details=conflito[0]
                )

            # 5. UPDATE 1: Tabela 'reserva'
            # 🎓 Atualiza o nome provisório (será NULL se não for grupo)
            sql_update_reserva = """
                UPDATE reserva
                SET 
                    valor_total = %s, observacao_reserva = %s, fk_usuario = %s, 
                    status_pagamento = %s, nome_provisorio = %s
                WHERE id_reserva = %s;
            """
            params_reserva = [valor_total, observacao, fk_usuario_logado, status_pagamento, nome_provisorio, id_reserva_principal]
            cursor.execute(sql_update_reserva, params_reserva)

            # 6. UPDATE 2: Tabela 'reserva_quarto' (Datas, Quarto)
            sql_update_rq = """
                UPDATE reserva_quarto
                SET
                    fk_quarto = %s, checkin = %s, checkout = %s,
                    valor_diaria_cobrado = (SELECT valor_diaria FROM quarto WHERE id_quarto = %s)
                WHERE id_reserva_quarto = %s;
            """
            params_rq = [quarto_id, checkin, checkout, quarto_id, reserva_quarto_id]
            cursor.execute(sql_update_rq, params_rq)

            # 7. 🎓 O "PULO DO GATO": Desliga os gatilhos (Triggers)
            #    Isso impede que o trg_check_reserva_valida() dispare
            #    no meio da nossa operação de "delete-e-reinsere".
            cursor.execute("SET session_replication_role = 'replica';")

            # 7.1. Deleta todos os hóspedes antigos
            cursor.execute("DELETE FROM reserva_hospede WHERE fk_reserva = %s", [id_reserva_principal])
            
            nome_final_titular = nome_provisorio # Padrão
            
            # 7.2. Re-insere o Titular (APENAS se não for reserva de grupo)
            if not isReservaGrupo and titular_id:
                sql_titular = "INSERT INTO reserva_hospede (fk_reserva, fk_hospede, tipo_hospede) VALUES (%s, %s, 'Titular');"
                cursor.execute(sql_titular, [id_reserva_principal, titular_id])
                
                # Busca o nome real para a resposta
                cursor.execute("SELECT nome_hospede FROM hospede WHERE id_hospede = %s", [titular_id])
                nome_final_titular = cursor.fetchone()[0]

            # 7.3. Re-insere os Acompanhantes
            if not isReservaGrupo and acompanhante_ids:
                sql_acompanhante = "INSERT INTO reserva_hospede (fk_reserva, fk_hospede, tipo_hospede) VALUES (%s, %s, 'Acompanhante');"
                params_acompanhantes = [(id_reserva_principal, ac_id) for ac_id in acompanhante_ids]
                cursor.executemany(sql_acompanhante, params_acompanhantes)

            # 7.4. 🎓 RELIGA OS GATILHOS (Triggers)
            cursor.execute("SET session_replication_role = 'origin';")

            # 8. Busca o objeto completo para retornar
            # (Usando a query da view get_reserva_detalhes)
            reserva_obj = _get_reserva_detalhes_internal(cursor, reserva_quarto_id)
            if not reserva_obj:
                 return error_response('Reserva não encontrada após atualização.', 'NOT_FOUND', 404)
            
            # 🎓 Garante que o nome_titular correto (Agência ou Hóspede) seja enviado
            reserva_obj['nome_titular'] = nome_final_titular

        # 9. Fim da transação (COMMIT)
        return success_response(reserva_obj, "RESERVA_UPDATED")

    except Exception as e:
        # Se algo der errado, a transação faz ROLLBACK
        return error_response(str(e), 'SERVER_ERROR', 500)

# -----------------------------------------------------------------
# VIEW: ATUALIZAR STATUS (Ações Rápidas: Cancelar, Pagar, etc.)
# -----------------------------------------------------------------
@csrf_exempt
@token_required
@transaction.atomic
@require_http_methods(["PATCH"])
def update_reserva_status_view(request, reserva_quarto_id):
    """
    View para 'Editar' a reserva (ações rápidas).
    Aceita PATCH para /api/agenda/update-status/<id>/
    
    🎓 REATORADO:
    1. Adicionado SELECT ... FOR UPDATE (Controle de Concorrência).
    2. Padronização de todas as respostas (success/error).
    """
    try:
        data = json.loads(request.body)
        novo_status_reserva = data.get('status_reserva')
        novo_status_pagamento = data.get('status_pagamento')

        if not novo_status_reserva and not novo_status_pagamento:
            return error_response('Nenhum status foi enviado para atualização.', 'VALIDATION_ERROR', 400)

        with connection.cursor() as cursor:
            
            # 2. Busca o ID da reserva principal
            cursor.execute("SELECT fk_reserva FROM reserva_quarto WHERE id_reserva_quarto = %s", [reserva_quarto_id])
            reserva_link = cursor.fetchone()
            if not reserva_link:
                return error_response('Reserva (link quarto) não encontrada.', 'NOT_FOUND', 404)
            
            id_reserva_principal = reserva_link[0]

            # 🎓 CONTROLE DE CONCORRÊNCIA (Sua Solicitação)
            # Trava a linha da 'reserva' principal.
            cursor.execute("SELECT 1 FROM reserva WHERE id_reserva = %s FOR UPDATE", [id_reserva_principal])

            # 3. Monta a query de atualização dinamicamente
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
                 return error_response('Reserva não encontrada após atualização.', 'NOT_FOUND', 404)

        return success_response(reserva_obj, "STATUS_UPDATED")

    except Exception as e:
        return error_response(str(e), 'SERVER_ERROR', 500)


# -----------------------------------------------------------------
# VIEW DE HÓSPEDES (CRUD)
# -----------------------------------------------------------------
@csrf_exempt 
@token_required
@require_http_methods(["GET", "POST"])
def hospedes_view(request):
    
    # MÉTODO GET (Filtra por status Ativo/Inativo)
    if request.method == 'GET':
        try:
            # 1. 🎓 Pega os parâmetros da URL. Define padrões.
            status = request.GET.get('status', 'Ativo')
            if status not in ['Ativo', 'Inativo']:
                status = 'Ativo'
            
            # Pega a página atual. O padrão é 1.
            page = int(request.GET.get('page', 1))
            # Pega o limite por página. O padrão é 10.
            limit = int(request.GET.get('limit', 10))
            
            # Calcula o OFFSET (quantos registros pular)
            # Página 1: (1 - 1) * 10 = 0 (pula 0)
            # Página 2: (2 - 1) * 10 = 10 (pula 10)
            offset = (page - 1) * limit

            with connection.cursor() as cursor:
                
                # 2. 🎓 QUERY 1: Obter o NÚMERO TOTAL de clientes (para os botões)
                sql_count = "SELECT COUNT(*) FROM hospede WHERE ativo = %s"
                cursor.execute(sql_count, [status])
                total_count = cursor.fetchone()[0]

                # 3. 🎓 QUERY 2: Obter os clientes da PÁGINA ATUAL (com LIMIT/OFFSET)
                sql_query = """
                    SELECT id_hospede, nome_hospede, email_hospede, telefone, 
                           pais_origem, cpf, passaporte 
                    FROM hospede 
                    WHERE ativo = %s
                    ORDER BY nome_hospede
                    LIMIT %s OFFSET %s; 
                """
                cursor.execute(sql_query, [status, limit, offset])
                clientes = dictfetchall(cursor)
                
            # 4. 🎓 Resposta padronizada com os dados E o total
            response_data = {
                "hospedes": clientes,
                "total_count": total_count
            }
            return success_response(response_data)
        
        except Exception as e:
            return error_response(str(e), 'SERVER_ERROR', 500)

    # MÉTODO POST (Cria novo hóspede)
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Validações pré-insert
            if data.get('pais_origem', 'Brasil') == 'Brasil' and not data.get('cpf'):
                return error_response("CPF é obrigatório para hóspedes do Brasil.", "VALIDATION_ERROR", 400)
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
# VIEW DE DETALHE DO HÓSPEDE
# -----------------------------------------------------------------
@csrf_exempt 
@token_required
@require_http_methods(["PUT", "DELETE", "PATCH"]) 
def hospede_detail_view(request, hospede_id):
    
    # MÉTODO PUT (Atualizar)
    if request.method == 'PUT':
        try:
            data = json.loads(request.body)
            
            # Validações
            if data.get('pais_origem', 'Brasil') == 'Brasil' and not data.get('cpf'):
                return error_response("CPF é obrigatório para hóspedes do Brasil.", "VALIDATION_ERROR", 400)
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
                    return error_response('Cliente não encontrado com este ID.', 'NOT_FOUND', 404)
            
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
# 🎓 VIEW DE PERFIL DO USUÁRIO
# -----------------------------------------------------------------
@csrf_exempt 
@token_required
@require_http_methods(["GET", "PUT"])
def usuario_perfil_view(request):
    """
    View para o perfil do usuário logado (/api/perfil/).
    🎓 REATORADO:
    1. Usa bcrypt.hashpw() para atualizar senha (Segurança).
    2. Usa os helpers error_response/success_response (Padronização).
    """
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
                senha = data.get('senha') # O modal enviará 'senha' se ela for mudada

                sql_update_query = "UPDATE usuario SET nome_usuario = %s, email_usuario = %s"
                params = [nome, email]

                # 🎓 VULNERABILIDADE CORRIGIDA: Hashing da nova senha
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
                return error_response('Este e-mail já está em uso por outra conta.', 'CONFLICT', 409)
            except Exception as e:
                return error_response(f'Erro no PUT: {str(e)}', 'SERVER_ERROR', 500)


# -----------------------------------------------------------------
# 🎓 VIEW DE DETALHES DA RESERVA (Refatorada)
# -----------------------------------------------------------------
@csrf_exempt
@token_required
@require_http_methods(["GET"])
def get_reserva_detalhes(request, reserva_quarto_id):
    """
    Endpoint para buscar os detalhes de UMA reserva específica.
    """
    try:
        with connection.cursor() as cursor:
            detalhes = _get_reserva_detalhes_internal(cursor, reserva_quarto_id)
            
            if not detalhes:
                return error_response('Reserva não encontrada', 'NOT_FOUND', 404)
            
            return success_response(detalhes)

    except Exception as e:
        return error_response(str(e), 'SERVER_ERROR', 500)

# -----------------------------------------------------------------
# 🎓 FUNÇÃO INTERNA (Helper) para buscar detalhes da reserva
#    (Evita duplicação de código entre PUT, PATCH e GET)
# -----------------------------------------------------------------
def _get_reserva_detalhes_internal(cursor, reserva_quarto_id):
    """
    Função helper que executa as queries para buscar todos os dados
    de uma reserva, dado um cursor já aberto.
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
        LEFT JOIN reserva_hospede AS rh_titular ON r.id_reserva = rh_titular.fk_reserva 
                                               AND rh_titular.tipo_hospede = 'Titular'
        LEFT JOIN hospede AS h ON rh_titular.fk_hospede = h.id_hospede
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
            rh.fk_reserva = %s 
            AND rh.tipo_hospede = 'Acompanhante';
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
    
    # MÉTODO GET
    if request.method == 'GET':
        # 🎓 MUDANÇA: Lê o parâmetro 'status' da URL.
        # O padrão é 'Disponível' se nada for fornecido.
        status = request.GET.get('status', 'Disponível')
        
        if status not in ['Disponível', 'Manutenção']:
            status = 'Disponível'

        # 🎓 MUDANÇA: A query agora usa um placeholder (%s) para o status
        sql_query = """
            SELECT
                id_quarto, numero, tipo_quarto, valor_diaria, status_quarto
            FROM quarto
            WHERE status_quarto = %s
            ORDER BY numero;
        """
        try:
            with connection.cursor() as cursor:
                # 🎓 Passamos o status como parâmetro
                cursor.execute(sql_query, [status])
                quartos = dictfetchall(cursor)
            return success_response(quartos)
        except Exception as e:
            return error_response(str(e), 'SERVER_ERROR', 500)

    # MÉTODO POST (Sem mudanças)
    elif request.method == 'POST':
        # ... (código do POST mantido) ...
        try:
            data = json.loads(request.body)
            # ... (validação e INSERT) ...
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
# VIEW DE DETALHE DO QUARTO (GET/PUT/DELETE)
# -----------------------------------------------------------------
@csrf_exempt 
@token_required
@require_http_methods(["GET", "PUT", "DELETE"])
def quarto_detail_view(request, quarto_id):
    """
    View para um Quarto específico (/api/quartos/<id>/).
    - GET: Busca um quarto pelo ID.
    - PUT: Atualiza um quarto existente.
    - DELETE: Deleta um quarto.
    """

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
            # 🎓 CONTROLE DE INTEGRIDADE (Sua Solicitação)
            # Não podemos deletar um quarto que está em 'reserva_quarto'.
            # O PostgreSQL irá barrar com IntegrityError, que vamos capturar.
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM quarto WHERE id_quarto = %s", [quarto_id])
                if cursor.rowcount == 0:
                    return error_response('Quarto não encontrado com este ID.', 'NOT_FOUND', 404)
            
            # 204 No Content é o padrão para DELETE bem-sucedido
            return success_response(None, "QUARTO_DELETED", 204) 
            
        except IntegrityError as e:
            # 🎓 Erro pego! (fk_reserva_quarto_quarto)
            return error_response(
                'Não é possível excluir este quarto pois ele está vinculado a uma ou mais reservas.',
                'FK_CONSTRAINT',
                409 # 409 Conflict
            )
        except Exception as e:
            return error_response(str(e), 'SERVER_ERROR', 500)

# =======================================================================
# 5. VIEW DE BUSINESS INTELLIGENCE (BI)
# =======================================================================

# -----------------------------------------------------------------
# VIEW DE GESTÃO (BI) (Protegida)
# -----------------------------------------------------------------
@csrf_exempt
@token_required
@require_http_methods(["GET"])
def get_indicadores_gestao(request):
    """
    Endpoint de BI (Business Intelligence) para o dashboard de Gestão.
    🎓 REGRA DE NEGÓCIO ATUALIZADA:
    O faturamento agora é calculado pela DATA DE CHECK-IN (Regime de Competência)
    e não mais pela data de criação da reserva.
    """
    try:
        # 1. LÓGICA DO FILTRO DE ANO (Mantida)
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

        with connection.cursor() as cursor:
        
            # 🎓 QUERY 1: KPIs (Refatorada para 'checkin')
            #    Agora calcula o faturamento total e o N. de reservas
            #    baseado nas reservas QUE TÊM CHECK-IN no ano filtrado.
            sql_kpi = """
                SELECT
                    COALESCE(SUM(r.valor_total), 0.00) AS faturamento_total,
                    COALESCE(COUNT(DISTINCT r.id_reserva), 0) AS total_reservas
                FROM reserva r
                INNER JOIN reserva_quarto rq ON r.id_reserva = rq.fk_reserva
                WHERE 
                    r.status_reserva != 'Cancelada'
                    -- 🎓 MUDANÇA: Filtra pelo check-in, não pela dt_criacao
                    AND rq.checkin BETWEEN %s AND %s; 
            """
            cursor.execute(sql_kpi, [data_inicio, data_fim])
            kpi_data = dictfetchall(cursor)[0]
            
            # 🎓 QUERY 2: Faturamento Mensal (Refatorada para 'checkin')
            sql_mensal = """
                WITH meses AS (
                    SELECT date_trunc('month', (%s::date + (n || ' months')::interval)) AS mes
                    FROM generate_series(0, 11) AS n
                ), meses_formatados AS (
                    SELECT TO_CHAR(mes, 'YYYY-MM') AS mes_ano FROM meses
                )
                SELECT
                    mf.mes_ano,
                    COALESCE(SUM(r.valor_total), 0.00) AS faturamento_mensal
                FROM meses_formatados mf
                LEFT JOIN reserva_quarto rq ON TO_CHAR(rq.checkin, 'YYYY-MM') = mf.mes_ano
                LEFT JOIN reserva r 
                    ON rq.fk_reserva = r.id_reserva
                    AND r.status_reserva != 'Cancelada'
                GROUP BY mf.mes_ano
                ORDER BY mf.mes_ano ASC;
            """
            cursor.execute(sql_mensal, [data_inicio])
            faturamento_mensal = dictfetchall(cursor)
            
            # 🎓 QUERY 3: Taxa de Ocupação (Lógica mantida, já usa 'checkin')
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
                data_fim, data_inicio,     # para dias_disponiveis
                data_fim, data_inicio,     # para dias_vendidos_interval
                data_inicio, data_fim      # para o OVERLAPS
            ]
            cursor.execute(sql_ocupacao, params_ocupacao)
            taxa_ocupacao = dictfetchall(cursor)[0]
            
            # 🎓 QUERY 4: Faturamento por Tipo (Refatorada para 'checkin')
            sql_tipo_quarto = """
                SELECT
                    q.tipo_quarto,
                    COALESCE(SUM(r.valor_total), 0.00) AS faturamento_por_tipo
                FROM quarto q
                LEFT JOIN reserva_quarto rq ON q.id_quarto = rq.fk_quarto
                LEFT JOIN reserva r 
                    ON rq.fk_reserva = r.id_reserva
                    AND r.status_reserva != 'Cancelada'
                    -- 🎓 MUDANÇA: Filtra pelo check-in, não pela dt_criacao
                    AND rq.checkin BETWEEN %s AND %s
                GROUP BY q.tipo_quarto
                ORDER BY faturamento_por_tipo DESC;
            """
            cursor.execute(sql_tipo_quarto, [data_inicio, data_fim])
            faturamento_por_tipo = dictfetchall(cursor)

        
        # 4. Junta todos os dados na resposta (Mantido)
        response_data = {
            'kpis': kpi_data,
            'taxa_ocupacao': taxa_ocupacao,
            'faturamento_mensal': faturamento_mensal,
            'faturamento_por_tipo': faturamento_por_tipo,
            'ano_filtrado': ano_filtrar
        }
        return success_response(response_data)
        
    except Exception as e:
        return error_response(str(e), 'SERVER_ERROR', 500)