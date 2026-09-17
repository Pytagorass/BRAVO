from django.db import connection

from ..db import dictfetchall


def buscar_indicadores(ano_filtrar):
    data_inicio = f"{ano_filtrar}-01-01"
    data_fim = f"{ano_filtrar}-12-31"
    status_template = ['Agendada', 'Ativa', 'Concluída', 'Cancelada']

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                COALESCE(SUM(r.valor_total), 0.00) AS faturamento_total,
                COALESCE(COUNT(DISTINCT r.id_reserva), 0) AS total_reservas
            FROM reserva r
            INNER JOIN reserva_quarto rq ON r.id_reserva = rq.fk_reserva
            WHERE
                r.status_reserva != 'Cancelada'
                AND rq.checkin BETWEEN %s AND %s;
            """,
            [data_inicio, data_fim],
        )
        kpi_data = dictfetchall(cursor)[0]

        cursor.execute(
            """
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
            """,
            [data_inicio, data_inicio, data_fim, data_inicio, data_fim],
        )
        faturamento_mensal = dictfetchall(cursor)

        cursor.execute(
            """
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
            """,
            [
                data_fim,
                data_inicio,
                data_fim,
                data_inicio,
                data_inicio,
                data_fim,
            ],
        )
        taxa_ocupacao = dictfetchall(cursor)[0]

        cursor.execute(
            """
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
            """,
            [data_inicio, data_fim],
        )
        faturamento_por_tipo = dictfetchall(cursor)

        cursor.execute(
            """
            SELECT
                r.status_reserva,
                COUNT(DISTINCT r.id_reserva) AS total
            FROM reserva r
            JOIN reserva_quarto rq ON rq.fk_reserva = r.id_reserva
            WHERE (rq.checkin, rq.checkout) OVERLAPS (%s::date, %s::date + interval '1 day')
            GROUP BY r.status_reserva;
            """,
            [data_inicio, data_fim],
        )
        reservas_status_raw = dictfetchall(cursor)
        status_map = {row['status_reserva']: int(row['total']) for row in reservas_status_raw}
        reservas_por_status = [
            {
                'status_reserva': status,
                'total': status_map.get(status, 0),
            }
            for status in status_template
        ]

        cursor.execute(
            """
            SELECT
                COALESCE(SUM(r.valor_total), 0.00) AS valor_pendente,
                COALESCE(COUNT(DISTINCT r.id_reserva), 0) AS reservas_em_aberto
            FROM reserva r
            JOIN reserva_quarto rq ON rq.fk_reserva = r.id_reserva
            WHERE
                r.status_reserva != 'Cancelada'
                AND r.status_pagamento IN ('Pendente','Em Partes')
                AND (rq.checkin, rq.checkout) OVERLAPS (%s::date, %s::date + interval '1 day');
            """,
            [data_inicio, data_fim],
        )
        pagamentos_pendentes = dictfetchall(cursor)[0]

        cursor.execute(
            """
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
            """,
            [data_inicio, data_fim, data_inicio, data_fim],
        )
        consumo_resumo = dictfetchall(cursor)[0]

        cursor.execute(
            """
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
            """,
            [data_inicio, data_fim, data_inicio, data_fim],
        )
        consumo_por_origem = dictfetchall(cursor)

        cursor.execute(
            """
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
            """,
            [data_inicio, data_fim, data_inicio, data_fim],
        )
        produtos_mais_vendidos = dictfetchall(cursor)

        cursor.execute(
            """
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
        )
        contas_consumo_abertas = dictfetchall(cursor)

    return {
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
        'ano_filtrado': ano_filtrar,
    }


def buscar_reservas_pendentes():
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
    with connection.cursor() as cursor:
        cursor.execute(sql)
        return dictfetchall(cursor)
