# =======================================================================
# 1. IMPORTAÇÕES
# =======================================================================
import json
import jwt
import datetime
from functools import wraps # Necessário para o decorador

# Importações do Django
from django.db import connection, IntegrityError, transaction
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

# --- Importa nosso decorador de autenticação (agora corrigido) ---
from .auth_decorator import token_required

# =======================================================================
# 2. FUNÇÃO UTILITÁRIA (Helper)
# =======================================================================
def dictfetchall(cursor):
    """
    Função utilitária (helper) que não faz parte do Django.
    Converte o resultado de cursor.fetchall() em uma lista de dicionários.
    """
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]

# =======================================================================
# 3. VIEWS DA API (Endpoints)
# =======================================================================

# -----------------------------------------------------------------
# VIEW DE LOGIN (NÃO protegida)
# -----------------------------------------------------------------
@csrf_exempt
def login_view(request):
    """
    Endpoint de login customizado.
    Recebe email/senha, consulta o banco com SQL puro e retorna um JWT.
    """
    
    if request.method != 'POST':
        return JsonResponse({'erro': 'Método não permitido'}, status=405)

    try:
        data = json.loads(request.body)
        email = data.get('email')
        senha = data.get('senha')

        if not email or not senha:
            return JsonResponse({'erro': 'Email e senha são obrigatórios'}, status=400)

        sql_query = """
            SELECT id_usuario, nome_usuario, email_usuario, tipo_usuario, senha
            FROM usuario
            WHERE email_usuario = %s AND ativo = 'Ativo';
        """

        with connection.cursor() as cursor:
            cursor.execute(sql_query, [email])
            user_data = dictfetchall(cursor)

            if not user_data:
                return JsonResponse({'erro': 'Credenciais inválidas ou usuário inativo'}, status=401)

            usuario = user_data[0]
            
            if usuario['senha'] != senha:
                return JsonResponse({'erro': 'Credenciais inválidas'}, status=401)

            payload = {
                'id_usuario': usuario['id_usuario'],
                'email': usuario['email_usuario'],
                'tipo_usuario': usuario['tipo_usuario'],
                'nome': usuario['nome_usuario'],
                'exp': datetime.datetime.utcnow() + datetime.timedelta(days=1),
                'iat': datetime.datetime.utcnow()
            }
            
            token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')

            return JsonResponse({
                'token': token,
                'usuario': {
                    'id': usuario['id_usuario'],
                    'nome': usuario['nome_usuario'],
                    'email': usuario['email_usuario'],
                    'tipo': usuario['tipo_usuario']
                }
            }, status=200)

    except Exception as e:
        return JsonResponse({'erro': f'Erro interno: {str(e)}'}, status=500)

# -----------------------------------------------------------------
# VIEW DA AGENDA (Gantt) (Protegida)
# -----------------------------------------------------------------
@csrf_exempt
@token_required 
def get_agenda_reservas(request):
    """
    Endpoint principal para carregar o Gráfico de Gantt.
    Protegido por JWT.
    
    🎓 SQL CORRIGIDO:
    Removemos a sub-query (SELECT aninhado) para 'nome_titular'
    e a substituímos por LEFT JOINs. Esta é uma forma muito mais
    robusta e eficiente de buscar os dados.
    """
    
    # 1. Esta é a consulta SQL otimizada
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
            
            -- 🎓 A MUDANÇA: Pegamos o nome do hóspede do LEFT JOIN
            h.nome_hospede AS nome_titular
            
        FROM 
            reserva_quarto AS rq
        
        -- Junta a reserva principal (INNER JOIN é obrigatório)
        INNER JOIN 
            reserva AS r ON rq.fk_reserva = r.id_reserva
        
        -- Junta o quarto (INNER JOIN é obrigatório)
        INNER JOIN 
            quarto AS q ON rq.fk_quarto = q.id_quarto
        
        -- 🎓 A MUDANÇA:
        -- Junta a tabela de hóspedes...
        LEFT JOIN
            reserva_hospede AS rh ON r.id_reserva = rh.fk_reserva 
                                  AND rh.tipo_hospede = 'Titular'
        
        -- ...e então junta a tabela de nomes
        LEFT JOIN
            hospede AS h ON rh.fk_hospede = h.id_hospede
            
    """

    try:
        # 2. Executa a nova consulta
        with connection.cursor() as cursor:
            cursor.execute(sql_query)
            reservas = dictfetchall(cursor)

        # 3. Retorna o JSON para o React
        return JsonResponse(reservas, safe=False)

    except Exception as e:
        # 4. Tratamento de erro
        return JsonResponse({'erro': str(e)}, status=500)
    

# -----------------------------------------------------------------
# VIEW DE CRIAÇÃO DE RESERVA (Protegida)
# -----------------------------------------------------------------
@csrf_exempt
@token_required 
@transaction.atomic
def reservas_view(request):
    """
    View para o CRUD de Reservas (/api/reservas/).
    - POST: Cria uma nova reserva (transacional).
    """
    
    if request.method == 'POST':
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
            
                # 2. VALIDAÇÃO DE OVERBOOKING (Sem mudanças)
                sql_check_overbooking = """
                    SELECT 1
                    FROM reserva_quarto rq
                    JOIN reserva r ON rq.fk_reserva = r.id_reserva
                    WHERE rq.fk_quarto = %s 
                      AND (rq.checkin, rq.checkout) OVERLAPS (%s, %s) 
                      AND r.status_reserva != 'Cancelada'
                    LIMIT 1;
                """
                cursor.execute(sql_check_overbooking, [quarto_id, checkin, checkout])
                if cursor.fetchone():
                    return JsonResponse({'erro': 'Overbooking', 'detail': 'Este quarto já está reservado.'}, status=400)

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
                # --- MUDANÇA: Adicionamos "RETURNING id_reserva_quarto" ---
                sql_quarto = """
                    INSERT INTO reserva_quarto (fk_reserva, fk_quarto, checkin, checkout, valor_diaria_cobrado)
                    VALUES (%s, %s, %s, %s, (SELECT valor_diaria FROM quarto WHERE id_quarto = %s))
                    RETURNING id_reserva_quarto;
                """
                params_quarto = [nova_reserva_id, quarto_id, checkin, checkout, quarto_id]
                cursor.execute(sql_quarto, params_quarto)
                nova_reserva_quarto_id = cursor.fetchone()[0] # <-- Pegamos o ID

                # 5. INSERT 3: Titular (Sem mudanças)
                sql_titular = "INSERT INTO reserva_hospede (fk_reserva, fk_hospede, tipo_hospede) VALUES (%s, %s, 'Titular');"
                cursor.execute(sql_titular, [nova_reserva_id, titular_id])

                # 6. INSERT 4...N: Acompanhantes (Sem mudanças)
                if acompanhante_ids:
                    sql_acompanhante = "INSERT INTO reserva_hospede (fk_reserva, fk_hospede, tipo_hospede) VALUES (%s, %s, 'Acompanhante');"
                    params_acompanhantes = [(nova_reserva_id, ac_id) for ac_id in acompanhante_ids]
                    cursor.executemany(sql_acompanhante, params_acompanhantes)
                
                # 7. --- MUDANÇA: Buscamos os dados para o front-end ---
                # Precisamos do nome do titular e do número do quarto
                cursor.execute("SELECT nome_hospede FROM hospede WHERE id_hospede = %s", [titular_id])
                nome_titular = cursor.fetchone()[0]
                
                cursor.execute("SELECT numero FROM quarto WHERE id_quarto = %s", [quarto_id])
                numero_quarto = cursor.fetchone()[0]

            # 8. --- MUDANÇA: Construímos o objeto de resposta ---
            # Este objeto tem o mesmo formato que o 'get_agenda_reservas'
            nova_reserva_obj = {
                'id_reserva_quarto': nova_reserva_quarto_id,
                'checkin': checkin,
                'checkout': checkout,
                'id_reserva': nova_reserva_id,
                'status_reserva': 'Agendada', # O status inicial é sempre 'Agendada'
                'status_pagamento': status_pagamento,
                'id_quarto': quarto_id,
                'numero_quarto': numero_quarto,
                'nome_titular': nome_titular
            }
            
            # 9. Retornamos 201 com o novo objeto
            return JsonResponse(nova_reserva_obj, status=201)
        
        except IntegrityError as e:
            return JsonResponse({'erro': f'Erro de integridade no banco: {str(e)}'}, status=400)
        except Exception as e:
            return JsonResponse({'erro': str(e)}, status=500)

    return JsonResponse({'erro': 'Método GET não permitido para esta rota'}, status=405)


# -----------------------------------------------------------------
# 🚀 VIEW: EDITAR RESERVA (Formulário Completo)
# -----------------------------------------------------------------
@csrf_exempt
@token_required
@transaction.atomic
def edit_reserva_view(request, reserva_quarto_id):
    """
    View para 'Editar' a reserva (Formulário completo).
    Aceita PUT para /api/agenda/editar/<id>/
    
    Esta view é complexa, pois atualiza a reserva principal,
    o quarto alocado (datas) e os hóspedes.
    """
    
    # 1. Esta view só aceita PUT
    if request.method != 'PUT':
        return JsonResponse({'erro': 'Método não permitido, use PUT'}, status=405)

    try:
        # 2. Extrai os dados do payload (do NovaReservaModal.js)
        data = json.loads(request.body)
        
        titular_id = int(data.get('fk_hospede_id_hospede'))
        quarto_id = int(data.get('quartos')[0]) # Assume [0] como na criação
        checkin = data.get('checkin')
        checkout = data.get('checkout')
        valor_total = data.get('valor_total')
        status_pagamento = data.get('forma_pagamento', 'Pendente')
        observacao = data.get('observacao_reserva')
        acompanhante_ids = data.get('acompanhantes', [])

        # Pega o usuário logado (que está fazendo a edição)
        fk_usuario_logado = request.user_token_payload.get('id_usuario')

        with connection.cursor() as cursor:
            
            # 3. Busca o ID da reserva principal
            cursor.execute("SELECT fk_reserva FROM reserva_quarto WHERE id_reserva_quarto = %s", [reserva_quarto_id])
            reserva_link = cursor.fetchone()
            if not reserva_link:
                return JsonResponse({'erro': 'Reserva (link quarto) não encontrada.'}, status=404)
            
            id_reserva_principal = reserva_link[0]

            # 4. VALIDAÇÃO DE OVERBOOKING (Modificada)
            #    Verifica conflitos de data, *excluindo* a própria reserva
            #    que estamos editando.
            sql_check_overbooking = """
                SELECT 1
                FROM reserva_quarto rq
                JOIN reserva r ON rq.fk_reserva = r.id_reserva
                WHERE rq.fk_quarto = %s 
                  AND (rq.checkin, rq.checkout) OVERLAPS (%s, %s) 
                  AND r.status_reserva != 'Cancelada'
                  AND rq.id_reserva_quarto != %s -- Exclui a própria reserva
                LIMIT 1;
            """
            cursor.execute(sql_check_overbooking, [quarto_id, checkin, checkout, reserva_quarto_id])
            if cursor.fetchone():
                return JsonResponse({'erro': 'Overbooking', 'detail': 'Este quarto já está reservado para este período.'}, status=400)

            # 5. UPDATE 1: Tabela 'reserva'
            sql_update_reserva = """
                UPDATE reserva
                SET 
                    valor_total = %s,
                    observacao_reserva = %s,
                    fk_usuario = %s, -- Atualiza para o último usuário que editou
                    status_pagamento = %s
                WHERE id_reserva = %s;
            """
            params_reserva = [valor_total, observacao, fk_usuario_logado, status_pagamento, id_reserva_principal]
            cursor.execute(sql_update_reserva, params_reserva)

            # 6. UPDATE 2: Tabela 'reserva_quarto'
            #    (Atualiza datas, o quarto e o valor da diária cobrada)
            sql_update_rq = """
                UPDATE reserva_quarto
                SET
                    fk_quarto = %s,
                    checkin = %s,
                    checkout = %s,
                    valor_diaria_cobrado = (SELECT valor_diaria FROM quarto WHERE id_quarto = %s)
                WHERE id_reserva_quarto = %s;
            """
            params_rq = [quarto_id, checkin, checkout, quarto_id, reserva_quarto_id]
            cursor.execute(sql_update_rq, params_rq)

            # 7. UPDATE 3: Hóspedes (Titular e Acompanhantes)
            #    Este é um "delete-e-reinsere", a forma mais simples de
            #    garantir que a lista de hóspedes está correta.
            
            # 7.1. Deleta todos os hóspedes (titular e acompanhantes)
            cursor.execute("DELETE FROM reserva_hospede WHERE fk_reserva = %s", [id_reserva_principal])

            # 7.2. Re-insere o Titular
            sql_titular = "INSERT INTO reserva_hospede (fk_reserva, fk_hospede, tipo_hospede) VALUES (%s, %s, 'Titular');"
            cursor.execute(sql_titular, [id_reserva_principal, titular_id])

            # 7.3. Re-insere os Acompanhantes
            if acompanhante_ids:
                sql_acompanhante = "INSERT INTO reserva_hospede (fk_reserva, fk_hospede, tipo_hospede) VALUES (%s, %s, 'Acompanhante');"
                params_acompanhantes = [(id_reserva_principal, ac_id) for ac_id in acompanhante_ids]
                cursor.executemany(sql_acompanhante, params_acompanhantes)

            # 8. 🚀 RETORNA O OBJETO ATUALIZADO
            #    Vamos re-usar a lógica de 'get_reserva_detalhes' para
            #    buscar os dados frescos e enviar de volta ao frontend.
            
            # 8.1. Query Principal
            sql_query_principal = """
                SELECT
                    r.id_reserva, r.status_reserva, r.status_pagamento, r.valor_total,
                    r.observacao_reserva, r.dt_criacao,
                    rq.id_reserva_quarto, rq.checkin, rq.checkout,
                    q.id_quarto, q.numero AS numero_quarto, q.tipo_quarto,
                    h_titular.id_hospede AS id_titular,
                    h_titular.nome_hospede AS nome_titular,
                    h_titular.email_hospede AS email_titular,
                    h_titular.telefone AS telefone_titular,
                    u.nome_usuario AS nome_usuario_criacao
                FROM reserva_quarto AS rq
                INNER JOIN reserva AS r ON rq.fk_reserva = r.id_reserva
                INNER JOIN quarto AS q ON rq.fk_quarto = q.id_quarto
                LEFT JOIN usuario AS u ON r.fk_usuario = u.id_usuario
                LEFT JOIN reserva_hospede AS rh_titular ON r.id_reserva = rh_titular.fk_reserva
                    AND rh_titular.tipo_hospede = 'Titular'
                LEFT JOIN hospede AS h_titular ON rh_titular.fk_hospede = h_titular.id_hospede
                WHERE rq.id_reserva_quarto = %s;
            """
            cursor.execute(sql_query_principal, [reserva_quarto_id])
            reserva_data = dictfetchall(cursor)

            if not reserva_data:
                return JsonResponse({'erro': 'Reserva não encontrada após atualização.'}, status=404)

            reserva_obj = reserva_data[0]
            
            # 8.2. Query Acompanhantes
            sql_query_acompanhantes = """
                SELECT h.id_hospede, h.nome_hospede
                FROM reserva_hospede AS rh
                INNER JOIN hospede AS h ON rh.fk_hospede = h.id_hospede
                WHERE
                    rh.fk_reserva = %s
                    AND rh.tipo_hospede = 'Acompanhante';
            """
            cursor.execute(sql_query_acompanhantes, [reserva_obj['id_reserva']])
            acompanhantes = dictfetchall(cursor)
            
            reserva_obj['acompanhantes'] = acompanhantes

            # 9. Retorna o objeto completo e atualizado
            return JsonResponse(reserva_obj, safe=False)

    except Exception as e:
        return JsonResponse({'erro': str(e)}, status=500)

# -----------------------------------------------------------------
# VIEW DE GESTÃO (BI) (Protegida)
# -----------------------------------------------------------------
@csrf_exempt
@token_required
def get_indicadores_gestao(request):
    """
    Endpoint de BI (Business Intelligence) para o dashboard de Gestão.
    Protegido por JWT.
    """
    
    if request.method == 'GET':
        try:
            kpi_data = {}
            faturamento_mensal = []

            with connection.cursor() as cursor:
            
                # QUERY 1: KPIs
                sql_kpi = """
                    SELECT
                        COALESCE(SUM(valor_total), 0) AS faturamento_total,
                        COALESCE(COUNT(id_reserva), 0) AS total_reservas
                    FROM reserva
                    WHERE status_reserva != 'Cancelada';
                """
                cursor.execute(sql_kpi)
                kpi_result = dictfetchall(cursor)
                if kpi_result:
                    kpi_data = kpi_result[0]
                
                # QUERY 2: Faturamento Mensal
                sql_mensal = """
                    SELECT
                        TO_CHAR(dt_criacao, 'YYYY-MM') AS mes_ano,
                        SUM(valor_total) AS faturamento_mensal
                    FROM reserva
                    WHERE status_reserva != 'Cancelada'
                    GROUP BY mes_ano
                    ORDER BY mes_ano DESC;
                """
                cursor.execute(sql_mensal)
                faturamento_mensal = dictfetchall(cursor)
            
            response_data = {
                'kpis': kpi_data,
                'faturamento_mensal': faturamento_mensal
            }
            return JsonResponse(response_data, safe=False)
            
        except Exception as e:
            return JsonResponse({'erro': str(e)}, status=500)
    
    return JsonResponse({'erro': 'Método não permitido'}, status=405)

# -----------------------------------------------------------------
# VIEW DE QUARTOS (CRUD) (Protegida)
# -----------------------------------------------------------------
@csrf_exempt 
@token_required
def quartos_view(request):
    """
    View unificada para o CRUD de Quartos (/api/quartos/).
    Protegido por JWT.
    """
    
    # MÉTODO GET
    if request.method == 'GET':
        sql_query = """
            SELECT
                id_quarto, numero, tipo_quarto, valor_diaria, status_quarto
            FROM quarto
            ORDER BY numero;
        """
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_query)
                quartos = dictfetchall(cursor)
            return JsonResponse(quartos, safe=False)
        except Exception as e:
            return JsonResponse({'erro': str(e)}, status=500)

    # MÉTODO POST
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            numero = data.get('numero')
            valor_diaria = data.get('valor_diaria')
            tipo_quarto = data.get('tipo_quarto')
            status_frontend = data.get('status_quarto') # 'Vazio' ou 'Manutenção'

            if status_frontend == 'Vazio':
                status_db = 'Disponível'
            else:
                status_db = 'Manutenção' 

            sql_insert = """
                INSERT INTO quarto (numero, valor_diaria, tipo_quarto, status_quarto)
                VALUES (%s, %s, %s, %s)
                RETURNING id_quarto;
            """
            params = [numero, valor_diaria, tipo_quarto, status_db]

            with connection.cursor() as cursor:
                cursor.execute(sql_insert, params)
                novo_quarto_id = cursor.fetchone()[0]
            
            return JsonResponse({'status': 'success', 'id_quarto': novo_quarto_id}, status=201)
        
        except IntegrityError as e:
            return JsonResponse({'erro': f'Erro: O número "{numero}" já está cadastrado.'}, status=400)
        except Exception as e:
            return JsonResponse({'erro': str(e)}, status=500)

    return JsonResponse({'erro': 'Método não permitido'}, status=405)


# -----------------------------------------------------------------
# 🚀 VIEW ATUALIZAR STATUS (Editar Reserva)
# -----------------------------------------------------------------
@csrf_exempt
@token_required
@transaction.atomic
def update_reserva_status_view(request, reserva_quarto_id):
    """
    View para 'Editar' a reserva (ações rápidas).
    Aceita PATCH para /api/agenda/update-status/<id>/
    
    Permite atualizar 'status_reserva' ou 'status_pagamento'.
    """
    
    # 1. Esta view só aceita PATCH
    if request.method != 'PATCH':
        return JsonResponse({'erro': 'Método não permitido, use PATCH'}, status=405)

    try:
        data = json.loads(request.body)
        novo_status_reserva = data.get('status_reserva')
        novo_status_pagamento = data.get('status_pagamento')

        # Validação: Pelo menos um campo deve ser enviado
        if not novo_status_reserva and not novo_status_pagamento:
            return JsonResponse({'erro': 'Nenhum status foi enviado para atualização.'}, status=400)

        with connection.cursor() as cursor:
            
            # 2. Precisamos do 'fk_reserva' para atualizar a tabela principal
            cursor.execute("SELECT fk_reserva FROM reserva_quarto WHERE id_reserva_quarto = %s", [reserva_quarto_id])
            reserva_link = cursor.fetchone()
            
            if not reserva_link:
                return JsonResponse({'erro': 'Reserva (link quarto) não encontrada.'}, status=404)
            
            id_reserva_principal = reserva_link[0]

            # 3. Monta a query de atualização dinamicamente
            campos_para_atualizar = []
            params = []

            if novo_status_reserva:
                campos_para_atualizar.append("status_reserva = %s")
                params.append(novo_status_reserva)
            
            if novo_status_pagamento:
                campos_para_atualizar.append("status_pagamento = %s")
                params.append(novo_status_pagamento)

            # Só executa se houver o que atualizar (redundante, mas seguro)
            if not campos_para_atualizar:
                return JsonResponse({'erro': 'Nenhum dado válido enviado.'}, status=400) # Nunca deve acontecer

            # 4. Executa o UPDATE na tabela 'reserva'
            sql_update = f"UPDATE reserva SET {', '.join(campos_para_atualizar)} WHERE id_reserva = %s"
            params.append(id_reserva_principal)
            
            cursor.execute(sql_update, params)

            # 5. 🚀 A MÁGICA: Retorna o objeto ATUALIZADO
            #    Após o update, chamamos a view 'get_reserva_detalhes'
            #    internamente para buscar e retornar os dados frescos.
            
            # (Re-busca os dados atualizados)
            # 5.1. Query Principal (copiada de get_reserva_detalhes)
            sql_query_principal = """
                SELECT
                    r.id_reserva, r.status_reserva, r.status_pagamento, r.valor_total,
                    r.observacao_reserva, r.dt_criacao,
                    rq.id_reserva_quarto, rq.checkin, rq.checkout,
                    q.id_quarto, q.numero AS numero_quarto, q.tipo_quarto,
                    h_titular.id_hospede AS id_titular,
                    h_titular.nome_hospede AS nome_titular,
                    h_titular.email_hospede AS email_titular,
                    h_titular.telefone AS telefone_titular,
                    u.nome_usuario AS nome_usuario_criacao
                FROM reserva_quarto AS rq
                INNER JOIN reserva AS r ON rq.fk_reserva = r.id_reserva
                INNER JOIN quarto AS q ON rq.fk_quarto = q.id_quarto
                LEFT JOIN usuario AS u ON r.fk_usuario = u.id_usuario
                LEFT JOIN reserva_hospede AS rh_titular ON r.id_reserva = rh_titular.fk_reserva
                    AND rh_titular.tipo_hospede = 'Titular'
                LEFT JOIN hospede AS h_titular ON rh_titular.fk_hospede = h_titular.id_hospede
                WHERE rq.id_reserva_quarto = %s;
            """
            cursor.execute(sql_query_principal, [reserva_quarto_id])
            reserva_data = dictfetchall(cursor)

            if not reserva_data:
                return JsonResponse({'erro': 'Reserva não encontrada após atualização.'}, status=404)

            reserva_obj = reserva_data[0]
            
            # 5.2. Query Acompanhantes (copiada de get_reserva_detalhes)
            sql_query_acompanhantes = """
                SELECT h.id_hospede, h.nome_hospede
                FROM reserva_hospede AS rh
                INNER JOIN hospede AS h ON rh.fk_hospede = h.id_hospede
                WHERE
                    rh.fk_reserva = %s
                    AND rh.tipo_hospede = 'Acompanhante';
            """
            cursor.execute(sql_query_acompanhantes, [reserva_obj['id_reserva']])
            acompanhantes = dictfetchall(cursor)
            
            reserva_obj['acompanhantes'] = acompanhantes

            # 6. Retorna o objeto completo e atualizado para o frontend
            return JsonResponse(reserva_obj, safe=False)

    except Exception as e:
        return JsonResponse({'erro': str(e)}, status=500)
 
# -----------------------------------------------------------------
# VIEW DE HÓSPEDES (CRUD) (Protegida)
# -----------------------------------------------------------------
@csrf_exempt 
@token_required
def hospedes_view(request):
    """
    View unificada para o CRUD de Hóspedes (/api/hospedes/).
    Protegido por JWT.
    """
    
    # MÉTODO GET
    if request.method == 'GET':
        sql_query = """
            SELECT id_hospede, nome_hospede, email_hospede, telefone, 
                   pais_origem, cpf, passaporte 
            FROM hospede 
            ORDER BY nome_hospede;
        """
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_query)
                clientes = dictfetchall(cursor)
            return JsonResponse(clientes, safe=False)
        except Exception as e:
            return JsonResponse({'erro': str(e)}, status=500)

    # MÉTODO POST
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            nome = data.get('nome_hospede')
            email = data.get('email_hospede')
            telefone = data.get('telefone')
            pais = data.get('pais_origem', 'Brasil')
            cpf = data.get('cpf') or None
            passaporte = data.get('passaporte') or None

            sql_insert = """
                INSERT INTO hospede 
                    (nome_hospede, email_hospede, telefone, pais_origem, cpf, passaporte)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id_hospede;
            """
            params = [nome, email, telefone, pais, cpf, passaporte]

            with connection.cursor() as cursor:
                cursor.execute(sql_insert, params)
                novo_hospede_id = cursor.fetchone()[0]
            
            return JsonResponse({'status': 'success', 'id_hospede': novo_hospede_id}, status=201)
        
        except IntegrityError as e:
            return JsonResponse({'erro': f'Erro de integridade: {str(e)}'}, status=400)
        except Exception as e:
            return JsonResponse({'erro': str(e)}, status=500)

    return JsonResponse({'erro': 'Método não permitido'}, status=405)

@csrf_exempt 
@token_required
def hospede_detail_view(request, hospede_id):
    """
    View unificada para um Hóspede específico (/api/hospedes/<id>/).
    - PUT: Atualiza um hóspede existente.
    - (Futuramente: GET para buscar 1, DELETE para apagar 1)
    """
    
    # ==========================================================
    # MÉTODO PUT: Atualizar um cliente (o que o modal de edição fará)
    # ==========================================================
    if request.method == 'PUT':
        try:
            # 1. Carrega os dados JSON enviados pelo ClienteModal.js
            data = json.loads(request.body)
            
            # 2. Extrai os dados (idêntico ao POST)
            nome = data.get('nome_hospede')
            email = data.get('email_hospede')
            telefone = data.get('telefone')
            pais = data.get('pais_origem', 'Brasil')
            cpf = data.get('cpf') or None
            passaporte = data.get('passaporte') or None

            # 3. 🎓 O SQL PURO (UPDATE)
            # Esta é a consulta de atualização.
            # Note a cláusula "WHERE id_hospede = %s".
            sql_update = """
                UPDATE hospede
                SET 
                    nome_hospede = %s, 
                    email_hospede = %s, 
                    telefone = %s, 
                    pais_origem = %s, 
                    cpf = %s, 
                    passaporte = %s
                WHERE 
                    id_hospede = %s;
            """
            
            # 4. 🎓 PREVENÇÃO DE SQL INJECTION
            # Os parâmetros devem estar na ordem exata dos placeholders (%s)
            params = [nome, email, telefone, pais, cpf, passaporte, hospede_id]

            with connection.cursor() as cursor:
                cursor.execute(sql_update, params)
                # O 'rowcount' verifica se alguma linha foi de fato alterada
                if cursor.rowcount == 0:
                    return JsonResponse({'erro': 'Cliente não encontrado com este ID.'}, status=404)
            
            # 5. Retorna sucesso (200 - OK)
            return JsonResponse({'status': 'success', 'id_hospede_atualizado': hospede_id}, status=200)
        
        except IntegrityError as e:
            # Erro de constraint (ex: email ou CPF duplicado)
            return JsonResponse({'erro': f'Erro de integridade: {str(e)}'}, status=400)
        except Exception as e:
            return JsonResponse({'erro': str(e)}, status=500)

    return JsonResponse({'erro': 'Método não permitido para esta rota'}, status=405)

@csrf_exempt 
@token_required
def quarto_detail_view(request, quarto_id):
    """
    View unificada para um Quarto específico (/api/quartos/<id>/).
    - PUT: Atualiza um quarto existente.
    """
    
    # ==========================================================
    # MÉTODO PUT: Atualizar um quarto (o que o modal de edição fará)
    # ==========================================================
    if request.method == 'PUT':
        try:
            # 1. Carrega os dados JSON enviados pelo QuartoModal.js
            data = json.loads(request.body)
            
            # 2. Extrai os dados
            numero = data.get('numero')
            valor_diaria = data.get('valor_diaria')
            tipo_quarto = data.get('tipo_quarto')
            status_frontend = data.get('status_quarto') # 'Vazio' ou 'Manutenção'

            # 3. 🎓 TRADUÇÃO (Anti-Corruption Layer)
            # Reutilizamos a lógica do POST: 'Vazio' (front) -> 'Disponível' (banco)
            if status_frontend == 'Vazio':
                status_db = 'Disponível'
            else:
                status_db = 'Manutenção' 

            # 4. 🎓 O SQL PURO (UPDATE)
            sql_update = """
                UPDATE quarto
                SET 
                    numero = %s, 
                    valor_diaria = %s, 
                    tipo_quarto = %s, 
                    status_quarto = %s
                WHERE 
                    id_quarto = %s;
            """
            
            # 5. Parâmetros na ordem correta
            params = [numero, valor_diaria, tipo_quarto, status_db, quarto_id]

            with connection.cursor() as cursor:
                cursor.execute(sql_update, params)
                if cursor.rowcount == 0:
                    return JsonResponse({'erro': 'Quarto não encontrado com este ID.'}, status=404)
            
            # 6. Retorna sucesso
            return JsonResponse({'status': 'success', 'id_quarto_atualizado': quarto_id}, status=200)
        
        except IntegrityError as e:
            # Erro de constraint (ex: 'numero' duplicado)
            return JsonResponse({'erro': f'Erro: O número "{numero}" já está cadastrado.'}, status=400)
        except Exception as e:
            return JsonResponse({'erro': str(e)}, status=500)

    return JsonResponse({'erro': 'Método não permitido para esta rota'}, status=405)

# -----------------------------------------------------------------
# 🚀 NOVA VIEW: PERFIL DO USUÁRIO LOGADO (para GET e PUT)
# -----------------------------------------------------------------
@csrf_exempt 
@token_required
def usuario_perfil_view(request):
    """
    View para o perfil do usuário logado (/api/perfil/).
    Usa o 'id_usuario' do token JWT.
    - GET: Busca os dados do perfil do usuário logado.
    - PUT: Atualiza o perfil do usuário logado.
    """
    
    # 1. 🎓 Pega o ID do usuário de dentro do token (injetado pelo @token_required)
    try:
        user_id = request.user_token_payload.get('id_usuario')
        if not user_id:
            return JsonResponse({'erro': 'Token inválido, ID de usuário não encontrado.'}, status=401)
    except Exception as e:
        return JsonResponse({'erro': f'Erro ao processar token: {str(e)}'}, status=401)

    # Abre a conexão
    with connection.cursor() as cursor:
        
        # ==========================================================
        # MÉTODO GET: Buscar dados para preencher o modal
        # ==========================================================
        if request.method == 'GET':
            try:
                # Buscamos apenas os campos editáveis (NÃO a senha)
                sql_get = "SELECT id_usuario, nome_usuario, email_usuario FROM usuario WHERE id_usuario = %s"
                cursor.execute(sql_get, [user_id])
                usuario = dictfetchall(cursor)
                
                if not usuario:
                    return JsonResponse({'erro': 'Usuário não encontrado no banco.'}, status=404)
                
                # Retorna o primeiro (e único) usuário
                return JsonResponse(usuario[0], safe=False)
            
            except Exception as e:
                return JsonResponse({'erro': f'Erro no GET: {str(e)}'}, status=500)

        # ==========================================================
        # MÉTODO PUT: Atualizar o perfil
        # ==========================================================
        elif request.method == 'PUT':
            try:
                data = json.loads(request.body)
                nome = data.get('nome_usuario')
                email = data.get('email_usuario')
                senha = data.get('senha') # O modal enviará 'senha' se ela for mudada

                # 🎓 SQL Dinâmico:
                # Vamos construir a query para atualizar a senha
                # APENAS se o usuário digitou uma nova.
                
                sql_update_query = "UPDATE usuario SET nome_usuario = %s, email_usuario = %s"
                params = [nome, email]

                # Se o campo 'senha' não for vazio, adiciona a atualização de senha
                if senha:
                    sql_update_query += ", senha = %s"
                    params.append(senha) # (Lembrete: estamos salvando em texto puro)

                # Adiciona o WHERE no final
                sql_update_query += " WHERE id_usuario = %s"
                params.append(user_id)
                
                cursor.execute(sql_update_query, params)
                
                if cursor.rowcount == 0:
                    return JsonResponse({'erro': 'Usuário não encontrado, nada atualizado.'}, status=404)

                return JsonResponse({'status': 'success', 'message': 'Perfil atualizado com sucesso.'}, status=200)

            except IntegrityError as e:
                return JsonResponse({'erro': 'Este e-mail já está em uso por outra conta.'}, status=400)
            except Exception as e:
                return JsonResponse({'erro': f'Erro no PUT: {str(e)}'}, status=500)

    return JsonResponse({'erro': 'Método não permitido'}, status=405)

@csrf_exempt
@token_required
def get_reserva_detalhes(request, reserva_quarto_id):
    """
    Endpoint para buscar os detalhes de UMA reserva específica.
    Chamado pelo ReservaDetalhesModal.js
    """
    if request.method != 'GET':
        return JsonResponse({'erro': 'Método não permitido'}, status=405)

    try:
        detalhes = {}
        acompanhantes = []
        
        with connection.cursor() as cursor:
            # Query 1: Busca os dados principais (Titular, Quarto, Usuário, etc.)
            sql_detalhes = """
                SELECT
                    r.id_reserva, r.valor_total, r.observacao_reserva, 
                    r.status_reserva, r.status_pagamento, r.dt_criacao,
                    
                    rq.id_reserva_quarto, rq.checkin, rq.checkout,
                    
                    q.numero AS numero_quarto, q.tipo_quarto,
                    
                    h.nome_hospede AS nome_titular,
                    h.email_hospede AS email_titular,
                    h.telefone AS telefone_titular,
                    
                    u.nome_usuario AS nome_usuario_criacao
                    
                FROM 
                    reserva_quarto AS rq
                JOIN 
                    reserva AS r ON rq.fk_reserva = r.id_reserva
                JOIN 
                    quarto AS q ON rq.fk_quarto = q.id_quarto
                JOIN 
                    usuario AS u ON r.fk_usuario = u.id_usuario
                    
                -- Pega o Titular
                LEFT JOIN 
                    reserva_hospede AS rh_titular ON r.id_reserva = rh_titular.fk_reserva 
                                                  AND rh_titular.tipo_hospede = 'Titular'
                LEFT JOIN 
                    hospede AS h ON rh_titular.fk_hospede = h.id_hospede
                    
                WHERE 
                    rq.id_reserva_quarto = %s;
            """
            cursor.execute(sql_detalhes, [reserva_quarto_id])
            detalhes_result = dictfetchall(cursor)
            
            if not detalhes_result:
                return JsonResponse({'erro': 'Reserva não encontrada'}, status=404)
            
            detalhes = detalhes_result[0]
            
            # Pega o ID da reserva principal para buscar os acompanhantes
            fk_reserva_principal = detalhes['id_reserva']
            
            # Query 2: Busca a lista de ACOMPANHANTES
            sql_acompanhantes = """
                SELECT
                    h.id_hospede, h.nome_hospede
                FROM 
                    reserva_hospede AS rh
                JOIN 
                    hospede AS h ON rh.fk_hospede = h.id_hospede
                WHERE 
                    rh.fk_reserva = %s 
                    AND rh.tipo_hospede = 'Acompanhante';
            """
            cursor.execute(sql_acompanhantes, [fk_reserva_principal])
            acompanhantes = dictfetchall(cursor)
            
            # Junta os resultados
            detalhes['acompanhantes'] = acompanhantes
            
            return JsonResponse(detalhes, safe=False)

    except Exception as e:
        return JsonResponse({'erro': str(e)}, status=500)