from django.db import connection

from ..db import dictfetchall


def buscar_categorias(ativo='Ativo'):
    filtros = []
    params = []
    if ativo != 'Todos':
        filtros.append('ativo = %s')
        params.append(ativo)

    where_clause = f"WHERE {' AND '.join(filtros)}" if filtros else ''
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
            params,
        )
        return dictfetchall(cursor)


def buscar_servicos(ativo='Ativo', categoria_id=None):
    filtros = []
    params = []

    if ativo != 'Todos':
        filtros.append('sl.ativo = %s')
        params.append(ativo)
    if categoria_id:
        filtros.append('sl.fk_categoria = %s')
        params.append(categoria_id)

    where_clause = f"WHERE {' AND '.join(filtros)}" if filtros else ''
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
            params,
        )
        return dictfetchall(cursor)


def buscar_ordens_por_conta(cursor, conta_id):
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
        [conta_id],
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
        [conta_id],
    )
    itens = dictfetchall(cursor)

    itens_por_ordem = {}
    for item in itens:
        itens_por_ordem.setdefault(item['fk_ordem'], []).append(item)

    for ordem in ordens:
        ordem['itens'] = itens_por_ordem.get(ordem['id_ordem'], [])

    return ordens


def buscar_ordens(status=None, conta_id=None, reserva_id=None):
    filtros = []
    params = []

    if status:
        filtros.append('ol.status_ordem = %s')
        params.append(status)
    if conta_id:
        filtros.append('ol.fk_conta = %s')
        params.append(conta_id)
    if reserva_id:
        filtros.append('ol.fk_reserva = %s')
        params.append(reserva_id)

    where_clause = f"WHERE {' AND '.join(filtros)}" if filtros else ''

    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT DISTINCT ol.fk_conta
            FROM ordem_lavanderia ol
            {where_clause}
            ORDER BY ol.fk_conta;
            """,
            params,
        )
        contas = [row[0] for row in cursor.fetchall()]

        ordens = []
        for conta in contas:
            ordens.extend(buscar_ordens_por_conta(cursor, conta))

    if status:
        ordens = [ordem for ordem in ordens if ordem['status_ordem'] == status]
    if conta_id:
        ordens = [ordem for ordem in ordens if ordem['fk_conta'] == conta_id]
    if reserva_id:
        ordens = [ordem for ordem in ordens if ordem['fk_reserva'] == reserva_id]

    return ordens


def buscar_servico_para_ordem(cursor, servico_id):
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
        [servico_id],
    )
    servico = dictfetchall(cursor)
    return servico[0] if servico else None


def criar_ordem(cursor, conta_id, reserva_id, usuario_id, observacao, total_ordem, prazo_horas):
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
        [conta_id, reserva_id, usuario_id, observacao, total_ordem, prazo_horas],
    )
    return dictfetchall(cursor)[0]


def criar_item_ordem(cursor, ordem_id, item):
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
            ordem_id,
            item['id_servico'],
            item['quantidade'],
            item['valor_unitario'],
            item['subtotal'],
            item['observacao'],
        ],
    )
    return dictfetchall(cursor)[0]


def registrar_historico_status(cursor, ordem_id, status_anterior, status_novo, usuario_id, observacao):
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
        [ordem_id, status_anterior, status_novo, usuario_id, observacao],
    )


def buscar_ordem_para_status(cursor, ordem_id):
    cursor.execute(
        """
        SELECT id_ordem, fk_conta, status_ordem, total_ordem
        FROM ordem_lavanderia
        WHERE id_ordem = %s
        FOR UPDATE;
        """,
        [ordem_id],
    )
    ordem = dictfetchall(cursor)
    return ordem[0] if ordem else None


def atualizar_status_ordem(cursor, ordem_id, novo_status):
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
        params,
    )
    ordem = dictfetchall(cursor)
    return ordem[0] if ordem else None


def abater_total_conta(cursor, conta_id, total_ordem):
    cursor.execute(
        """
        UPDATE conta_consumo
        SET total_acumulado = GREATEST(total_acumulado - %s, 0)
        WHERE id_conta = %s;
        """,
        [total_ordem, conta_id],
    )
