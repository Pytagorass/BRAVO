from django.db import connection

from ..db import dictfetchall
from . import lavanderia_repository


def buscar_reservas_abertas():
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
        return dictfetchall(cursor)


def buscar_reserva_para_consumo(cursor, reserva_id):
    cursor.execute(
        """
        SELECT id_reserva, status_reserva
        FROM reserva
        WHERE id_reserva = %s
        FOR UPDATE;
        """,
        [reserva_id],
    )
    reserva = dictfetchall(cursor)
    return reserva[0] if reserva else None


def buscar_ou_criar_conta_consumo(cursor, reserva_id):
    cursor.execute(
        """
        INSERT INTO conta_consumo (fk_reserva)
        VALUES (%s)
        ON CONFLICT (fk_reserva) DO UPDATE
            SET fk_reserva = EXCLUDED.fk_reserva
        RETURNING id_conta, status_conta;
        """,
        [reserva_id],
    )
    conta = dictfetchall(cursor)
    return conta[0] if conta else None


def buscar_produto_para_venda(cursor, produto_id):
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
        [produto_id],
    )
    produto = dictfetchall(cursor)
    return produto[0] if produto else None


def criar_venda(cursor, conta_id, reserva_id, usuario_id, origem, observacao, total_venda):
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
        [conta_id, reserva_id, usuario_id, origem, observacao, total_venda],
    )
    return dictfetchall(cursor)[0]


def criar_item_venda(cursor, venda_id, item):
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
            venda_id,
            item['id_produto'],
            item['quantidade'],
            item['valor_unitario'],
            item['subtotal'],
            item['observacao'],
        ],
    )
    return dictfetchall(cursor)[0]


def atualizar_estoque_produto(cursor, produto_id, estoque_posterior):
    cursor.execute(
        """
        UPDATE produto
        SET estoque_atual = %s, dt_atualizacao = NOW()
        WHERE id_produto = %s;
        """,
        [estoque_posterior, produto_id],
    )


def registrar_movimento_estoque(
    cursor,
    produto_id,
    usuario_id,
    item_venda_id,
    quantidade,
    estoque_anterior,
    estoque_posterior,
    observacao,
):
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
            produto_id,
            usuario_id,
            item_venda_id,
            quantidade,
            estoque_anterior,
            estoque_posterior,
            observacao,
        ],
    )


def incrementar_total_conta(cursor, conta_id, total_venda):
    cursor.execute(
        """
        UPDATE conta_consumo
        SET total_acumulado = total_acumulado + %s
        WHERE id_conta = %s
        RETURNING total_acumulado::float AS total_acumulado;
        """,
        [total_venda, conta_id],
    )
    conta = dictfetchall(cursor)
    return conta[0] if conta else None


def buscar_conta_detalhe(conta_id):
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
            [conta_id],
        )
        conta = dictfetchall(cursor)
        if not conta:
            return None

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
            [conta_id],
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
            [conta_id],
        )
        itens = dictfetchall(cursor)
        ordens_lavanderia = lavanderia_repository.buscar_ordens_por_conta(cursor, conta_id)

    itens_por_venda = {}
    for item in itens:
        itens_por_venda.setdefault(item['fk_venda'], []).append(item)

    for venda in vendas:
        venda['itens'] = itens_por_venda.get(venda['id_venda'], [])

    response = conta[0]
    response['vendas'] = vendas
    response['ordens_lavanderia'] = ordens_lavanderia
    return response


def fechar_conta(conta_id):
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
            [conta_id],
        )
        conta = dictfetchall(cursor)

    return conta[0] if conta else None
