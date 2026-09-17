from django.db import connection

from ..db import dictfetchall


def buscar_agenda_reservas():
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
        FROM reserva_quarto AS rq
        INNER JOIN reserva AS r ON rq.fk_reserva = r.id_reserva
        INNER JOIN quarto AS q ON rq.fk_quarto = q.id_quarto
        LEFT JOIN hospede AS h ON r.fk_hospede_titular = h.id_hospede
        LEFT JOIN barco AS b ON r.fk_barco = b.id_barco
        LEFT JOIN tipo_passeio AS tp ON r.fk_tipo_passeio = tp.id_tipo_passeio;
    """
    with connection.cursor() as cursor:
        cursor.execute(sql_query)
        return dictfetchall(cursor)


def buscar_reserva_detalhes(reserva_quarto_id, cursor=None):
    owns_cursor = cursor is None
    if owns_cursor:
        cursor_context = connection.cursor()
        cursor = cursor_context.__enter__()

    try:
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
            FROM reserva_quarto AS rq
            JOIN reserva AS r ON rq.fk_reserva = r.id_reserva
            JOIN quarto AS q ON rq.fk_quarto = q.id_quarto
            LEFT JOIN barco AS b ON r.fk_barco = b.id_barco
            LEFT JOIN tipo_passeio AS tp ON r.fk_tipo_passeio = tp.id_tipo_passeio
            LEFT JOIN usuario AS u ON r.fk_usuario = u.id_usuario
            LEFT JOIN hospede AS h ON r.fk_hospede_titular = h.id_hospede
            WHERE rq.id_reserva_quarto = %s;
        """
        cursor.execute(sql_detalhes, [reserva_quarto_id])
        detalhes_result = dictfetchall(cursor)
        if not detalhes_result:
            return None

        detalhes = detalhes_result[0]
        cursor.execute(
            """
            SELECT h.id_hospede, h.nome_hospede
            FROM reserva_hospede AS rh
            JOIN hospede AS h ON rh.fk_hospede = h.id_hospede
            WHERE rh.fk_reserva = %s;
            """,
            [detalhes['id_reserva']],
        )
        detalhes['acompanhantes'] = dictfetchall(cursor)
        return detalhes
    finally:
        if owns_cursor:
            cursor_context.__exit__(None, None, None)


def bloquear_quarto(cursor, quarto_id):
    cursor.execute(
        """
        SELECT id_quarto, numero, status_quarto, valor_diaria
        FROM quarto
        WHERE id_quarto = %s
        FOR UPDATE;
        """,
        [quarto_id],
    )
    quarto = dictfetchall(cursor)
    return quarto[0] if quarto else None


def bloquear_barco(cursor, barco_id):
    cursor.execute(
        """
        SELECT id_barco, nome_barco, capacidade_pessoas, status_barco
        FROM barco
        WHERE id_barco = %s
        FOR UPDATE;
        """,
        [barco_id],
    )
    barco = dictfetchall(cursor)
    return barco[0] if barco else None


def buscar_tipo_passeio_ativo(cursor, tipo_passeio_id):
    cursor.execute(
        """
        SELECT id_tipo_passeio, nome_tipo
        FROM tipo_passeio
        WHERE id_tipo_passeio = %s AND ativo = 'Ativo';
        """,
        [tipo_passeio_id],
    )
    tipo_passeio = dictfetchall(cursor)
    return tipo_passeio[0] if tipo_passeio else None


def buscar_conflito_barco(cursor, barco_id, data_embarque, data_desembarque, reserva_id_atual=None):
    params = [barco_id, data_embarque, data_desembarque]
    filtro_reserva_atual = ''
    if reserva_id_atual:
        filtro_reserva_atual = 'AND r.id_reserva != %s'
        params.append(reserva_id_atual)

    cursor.execute(
        f"""
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
        """,
        params,
    )
    conflito = dictfetchall(cursor)
    return conflito[0] if conflito else None


def buscar_conflito_quarto(cursor, quarto_id, checkin, checkout, reserva_quarto_id=None):
    params = [quarto_id, checkin, checkout]
    filtro_reserva_quarto = ''
    if reserva_quarto_id:
        filtro_reserva_quarto = 'AND rq.id_reserva_quarto != %s'
        params.append(reserva_quarto_id)

    cursor.execute(
        f"""
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
          {filtro_reserva_quarto}
        LIMIT 1;
        """,
        params,
    )
    conflito = dictfetchall(cursor)
    return conflito[0] if conflito else None


def criar_reserva(cursor, payload):
    cursor.execute(
        """
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
        """,
        [
            payload['valor_total'],
            payload['observacao_reserva'],
            payload['usuario_id'],
            payload['status_pagamento'],
            payload['titular_id'],
            payload['fk_barco'],
            payload['fk_tipo_passeio'],
            payload['data_embarque'],
            payload['data_desembarque'],
            payload['local_embarque'],
            payload['local_desembarque'],
            payload['observacao_operacional'],
        ],
    )
    return cursor.fetchone()[0]


def criar_reserva_quarto(cursor, reserva_id, quarto_id, checkin, checkout, valor_diaria):
    cursor.execute(
        """
        INSERT INTO reserva_quarto (
            fk_reserva,
            fk_quarto,
            checkin,
            checkout,
            valor_diaria_cobrado
        )
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id_reserva_quarto;
        """,
        [reserva_id, quarto_id, checkin, checkout, valor_diaria],
    )
    return cursor.fetchone()[0]


def inserir_acompanhantes(cursor, reserva_id, acompanhante_ids):
    if not acompanhante_ids:
        return

    cursor.executemany(
        """
        INSERT INTO reserva_hospede (fk_reserva, fk_hospede)
        VALUES (%s, %s);
        """,
        [(reserva_id, acompanhante_id) for acompanhante_id in acompanhante_ids],
    )


def buscar_nome_hospede(cursor, hospede_id):
    cursor.execute("SELECT nome_hospede FROM hospede WHERE id_hospede = %s", [hospede_id])
    row = cursor.fetchone()
    return row[0] if row else None


def buscar_reserva_quarto_para_edicao(cursor, reserva_quarto_id):
    cursor.execute(
        """
        SELECT
            rq.fk_reserva,
            rq.fk_quarto,
            rq.checkin,
            rq.checkout,
            r.status_reserva
        FROM reserva_quarto rq
        JOIN reserva r ON rq.fk_reserva = r.id_reserva
        WHERE rq.id_reserva_quarto = %s
        FOR UPDATE;
        """,
        [reserva_quarto_id],
    )
    reserva_data = dictfetchall(cursor)
    return reserva_data[0] if reserva_data else None


def atualizar_reserva_principal(cursor, reserva_id, payload):
    cursor.execute(
        """
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
        """,
        [
            payload['valor_total'],
            payload['observacao_reserva'],
            payload['usuario_id'],
            payload['status_pagamento'],
            payload['titular_id'],
            payload['fk_barco'],
            payload['fk_tipo_passeio'],
            payload['data_embarque'],
            payload['data_desembarque'],
            payload['local_embarque'],
            payload['local_desembarque'],
            payload['observacao_operacional'],
            reserva_id,
        ],
    )


def atualizar_reserva_quarto(cursor, reserva_quarto_id, quarto_id, checkin, checkout, valor_diaria):
    cursor.execute(
        """
        UPDATE reserva_quarto
        SET
            fk_quarto = %s,
            checkin = %s,
            checkout = %s,
            valor_diaria_cobrado = %s
        WHERE id_reserva_quarto = %s;
        """,
        [quarto_id, checkin, checkout, valor_diaria, reserva_quarto_id],
    )


def substituir_acompanhantes(cursor, reserva_id, acompanhante_ids):
    cursor.execute("DELETE FROM reserva_hospede WHERE fk_reserva = %s", [reserva_id])
    inserir_acompanhantes(cursor, reserva_id, acompanhante_ids)


def buscar_reserva_id_por_reserva_quarto(cursor, reserva_quarto_id):
    cursor.execute(
        "SELECT fk_reserva FROM reserva_quarto WHERE id_reserva_quarto = %s",
        [reserva_quarto_id],
    )
    row = cursor.fetchone()
    return row[0] if row else None


def bloquear_reserva(cursor, reserva_id):
    cursor.execute("SELECT 1 FROM reserva WHERE id_reserva = %s FOR UPDATE", [reserva_id])
    return cursor.fetchone() is not None


def atualizar_status_reserva(cursor, reserva_id, campos):
    set_clauses = []
    params = []

    for field, value in campos.items():
        set_clauses.append(f"{field} = %s")
        params.append(value)

    params.append(reserva_id)
    cursor.execute(
        f"UPDATE reserva SET {', '.join(set_clauses)} WHERE id_reserva = %s",
        params,
    )
