-- ===================================================================
-- Seed de demonstracao para o modulo de consumo
-- Projeto: BRAVO
--
-- Objetivo:
--   Popular categorias, produtos, estoque e vendas de consumo para que
--   a pagina de Gestao tenha massa de dados realista.
--
-- Como executar:
--   psql -U postgres -d Barco_Hotel -f scripts/postgres/004_seed_consumo_demo.sql
--
-- Observacao:
--   O script e idempotente. Produtos/categorias usam ON CONFLICT e as
--   vendas do seed sao identificadas por observacao fixa.
-- ===================================================================

BEGIN;

INSERT INTO categoria_produto (nome_categoria, tipo_categoria)
VALUES
    ('Bebidas', 'Restaurante'),
    ('Lembrancas', 'Lojinha'),
    ('Vestuarios', 'Lojinha'),
    ('Utilidades', 'Lojinha'),
    ('Pesca', 'Lojinha')
ON CONFLICT (nome_categoria, tipo_categoria) DO NOTHING;

INSERT INTO produto (
    fk_categoria,
    nome_produto,
    descricao,
    preco_atual,
    controla_estoque,
    estoque_atual,
    estoque_minimo
)
SELECT
    cp.id_categoria,
    seed.nome_produto,
    seed.descricao,
    seed.preco_atual,
    seed.controla_estoque,
    seed.estoque_atual,
    seed.estoque_minimo
FROM (
    VALUES
        ('Restaurante', 'Bebidas', 'Agua Mineral 500ml', 'Garrafa sem gas.', 5.00, TRUE, 160, 30),
        ('Restaurante', 'Bebidas', 'Refrigerante Lata', 'Lata 350ml sabores variados.', 7.00, TRUE, 120, 24),
        ('Restaurante', 'Bebidas', 'Suco Natural', 'Suco natural preparado na cozinha.', 12.00, FALSE, 0, 0),
        ('Restaurante', 'Bebidas', 'Caipirinha', 'Drink classico servido no bar.', 22.00, FALSE, 0, 0),
        ('Lojinha', 'Lembrancas', 'Ima Pantanal', 'Ima decorativo do Pantanal.', 12.00, TRUE, 80, 15),
        ('Lojinha', 'Lembrancas', 'Caneca BRAVO', 'Caneca personalizada BRAVO.', 35.00, TRUE, 40, 8),
        ('Lojinha', 'Lembrancas', 'Cartao Postal', 'Cartao postal tematico.', 6.00, TRUE, 120, 25),
        ('Lojinha', 'Vestuarios', 'Camiseta BRAVO', 'Camiseta algodao com logo BRAVO.', 75.00, TRUE, 35, 8),
        ('Lojinha', 'Vestuarios', 'Bone Bordado', 'Bone bordado com marca BRAVO.', 55.00, TRUE, 28, 6),
        ('Lojinha', 'Vestuarios', 'Camisa UV Pesca', 'Camisa UV para pesca esportiva.', 130.00, TRUE, 18, 5),
        ('Lojinha', 'Utilidades', 'Garrafa Termica', 'Garrafa termica para passeio.', 95.00, TRUE, 16, 4),
        ('Lojinha', 'Utilidades', 'Protetor Solar', 'Protetor solar FPS 50.', 48.00, TRUE, 32, 8),
        ('Lojinha', 'Utilidades', 'Repelente', 'Repelente corporal.', 35.00, TRUE, 36, 8),
        ('Lojinha', 'Pesca', 'Isca Artificial', 'Isca artificial para pesca.', 42.00, TRUE, 44, 10),
        ('Lojinha', 'Pesca', 'Linha de Pesca', 'Linha de pesca 100m.', 30.00, TRUE, 30, 8)
) AS seed (
    tipo_categoria,
    nome_categoria,
    nome_produto,
    descricao,
    preco_atual,
    controla_estoque,
    estoque_atual,
    estoque_minimo
)
JOIN categoria_produto cp
  ON cp.tipo_categoria = seed.tipo_categoria::tipo_categoria_consumo_enum
 AND cp.nome_categoria = seed.nome_categoria
ON CONFLICT (fk_categoria, nome_produto) DO NOTHING;

INSERT INTO movimento_estoque (
    fk_produto,
    fk_usuario,
    tipo_movimento,
    quantidade,
    estoque_anterior,
    estoque_posterior,
    observacao
)
SELECT
    p.id_produto,
    u.id_usuario,
    'Entrada',
    p.estoque_atual,
    0,
    p.estoque_atual,
    'Seed BRAVO - estoque inicial'
FROM produto p
CROSS JOIN (
    SELECT id_usuario
    FROM usuario
    ORDER BY id_usuario
    LIMIT 1
) u
WHERE
    p.controla_estoque = TRUE
    AND p.estoque_atual > 0
    AND NOT EXISTS (
        SELECT 1
        FROM movimento_estoque me
        WHERE
            me.fk_produto = p.id_produto
            AND me.observacao = 'Seed BRAVO - estoque inicial'
    );

DO $$
DECLARE
    v_usuario INTEGER;
    v_reserva INTEGER;
    v_conta INTEGER;
    v_venda INTEGER;
    v_item INTEGER;
    v_total NUMERIC(10, 2);
    v_item_total NUMERIC(10, 2);
    v_estoque_anterior INTEGER;
    v_estoque_posterior INTEGER;
    venda RECORD;
    item RECORD;
    produto_atual RECORD;
BEGIN
    SELECT id_usuario
    INTO v_usuario
    FROM usuario
    ORDER BY id_usuario
    LIMIT 1;

    IF v_usuario IS NULL THEN
        RAISE EXCEPTION 'Nenhum usuario encontrado para vincular as vendas de consumo.';
    END IF;

    SELECT id_reserva
    INTO v_reserva
    FROM reserva
    WHERE status_reserva = 'Ativa'
    ORDER BY id_reserva DESC
    LIMIT 1;

    IF v_reserva IS NULL THEN
        SELECT id_reserva
        INTO v_reserva
        FROM reserva
        WHERE status_reserva <> 'Cancelada'
        ORDER BY id_reserva DESC
        LIMIT 1;
    END IF;

    IF v_reserva IS NULL THEN
        RAISE NOTICE 'Nenhuma reserva disponivel para criar vendas de consumo.';
        RETURN;
    END IF;

    INSERT INTO conta_consumo (fk_reserva)
    VALUES (v_reserva)
    ON CONFLICT (fk_reserva) DO NOTHING;

    SELECT id_conta
    INTO v_conta
    FROM conta_consumo
    WHERE fk_reserva = v_reserva
      AND status_conta = 'Aberta';

    IF v_conta IS NULL THEN
        RAISE NOTICE 'A reserva % nao possui conta aberta para receber seed de consumo.', v_reserva;
        RETURN;
    END IF;

    FOR venda IN
        SELECT *
        FROM (
            VALUES
                ('seed-001', 'Restaurante', TIMESTAMPTZ '2026-09-14 12:40:00-04'),
                ('seed-002', 'Lojinha',     TIMESTAMPTZ '2026-09-14 18:15:00-04'),
                ('seed-003', 'Restaurante', TIMESTAMPTZ '2026-09-15 13:05:00-04'),
                ('seed-004', 'Lojinha',     TIMESTAMPTZ '2026-09-15 19:10:00-04'),
                ('seed-005', 'Restaurante', TIMESTAMPTZ '2026-09-16 12:20:00-04'),
                ('seed-006', 'Restaurante', TIMESTAMPTZ '2026-09-16 20:35:00-04'),
                ('seed-007', 'Lojinha',     TIMESTAMPTZ '2026-09-17 10:05:00-04'),
                ('seed-008', 'Restaurante', TIMESTAMPTZ '2026-09-17 16:30:00-04'),
                ('seed-009', 'Lojinha',     TIMESTAMPTZ '2026-09-18 09:20:00-04'),
                ('seed-010', 'Restaurante', TIMESTAMPTZ '2026-09-18 14:15:00-04')
        ) AS v(codigo, origem, criado_em)
    LOOP
        IF EXISTS (
            SELECT 1
            FROM venda_consumo
            WHERE observacao = 'Seed BRAVO consumo ' || venda.codigo
        ) THEN
            CONTINUE;
        END IF;

        INSERT INTO venda_consumo (
            fk_conta,
            fk_reserva,
            fk_usuario,
            origem,
            observacao,
            total_venda,
            dt_criacao
        )
        VALUES (
            v_conta,
            v_reserva,
            v_usuario,
            venda.origem::tipo_categoria_consumo_enum,
            'Seed BRAVO consumo ' || venda.codigo,
            0.00,
            venda.criado_em
        )
        RETURNING id_venda INTO v_venda;

        v_total := 0.00;

        FOR item IN
            SELECT *
            FROM (
                VALUES
                    ('seed-001', 'Cerveja Skol 600', 3, 'Consumo no almoco'),
                    ('seed-001', 'Agua Mineral 500ml', 2, 'Passeio'),
                    ('seed-002', 'Chaveiro Capivara', 2, 'Lembranca'),
                    ('seed-002', 'Ima Pantanal', 1, 'Lembranca'),
                    ('seed-003', 'Refrigerante Lata', 2, 'Bebidas'),
                    ('seed-004', 'Camiseta BRAVO', 1, 'Tamanho M'),
                    ('seed-004', 'Bone Bordado', 1, 'Azul'),
                    ('seed-005', 'Suco Natural', 2, 'Bebidas'),
                    ('seed-006', 'Cerveja Skol 600', 4, 'Bebidas'),
                    ('seed-007', 'Caneca BRAVO', 2, 'Presentes'),
                    ('seed-007', 'Cartao Postal', 4, 'Lembrancas'),
                    ('seed-008', 'Agua Mineral 500ml', 3, 'Passeio'),
                    ('seed-009', 'Protetor Solar', 1, 'Lojinha'),
                    ('seed-009', 'Repelente', 1, 'Lojinha'),
                    ('seed-010', 'Caipirinha', 2, 'Bebidas')
            ) AS i(codigo, nome_produto, quantidade, observacao)
            WHERE i.codigo = venda.codigo
        LOOP
            SELECT
                p.id_produto,
                p.preco_atual,
                p.controla_estoque,
                p.estoque_atual
            INTO produto_atual
            FROM produto p
            WHERE p.nome_produto = item.nome_produto
            ORDER BY p.id_produto
            LIMIT 1
            FOR UPDATE;

            IF NOT FOUND THEN
                RAISE NOTICE 'Produto nao encontrado no seed: %', item.nome_produto;
                CONTINUE;
            END IF;

            v_item_total := produto_atual.preco_atual * item.quantidade;

            INSERT INTO item_venda_consumo (
                fk_venda,
                fk_produto,
                quantidade,
                valor_unitario,
                subtotal,
                observacao,
                dt_criacao
            )
            VALUES (
                v_venda,
                produto_atual.id_produto,
                item.quantidade,
                produto_atual.preco_atual,
                v_item_total,
                item.observacao,
                venda.criado_em
            )
            RETURNING id_item INTO v_item;

            IF produto_atual.controla_estoque THEN
                v_estoque_anterior := produto_atual.estoque_atual;
                v_estoque_posterior := GREATEST(produto_atual.estoque_atual - item.quantidade, 0);

                UPDATE produto
                SET
                    estoque_atual = v_estoque_posterior,
                    dt_atualizacao = NOW()
                WHERE id_produto = produto_atual.id_produto;

                INSERT INTO movimento_estoque (
                    fk_produto,
                    fk_usuario,
                    fk_item_venda,
                    tipo_movimento,
                    quantidade,
                    estoque_anterior,
                    estoque_posterior,
                    observacao,
                    dt_criacao
                )
                VALUES (
                    produto_atual.id_produto,
                    v_usuario,
                    v_item,
                    'Saida',
                    item.quantidade,
                    v_estoque_anterior,
                    v_estoque_posterior,
                    'Seed BRAVO consumo ' || venda.codigo,
                    venda.criado_em
                );
            END IF;

            v_total := v_total + v_item_total;
        END LOOP;

        UPDATE venda_consumo
        SET total_venda = v_total
        WHERE id_venda = v_venda;
    END LOOP;

    UPDATE conta_consumo cc
    SET total_acumulado = (
        SELECT COALESCE(SUM(vc.total_venda), 0.00)
        FROM venda_consumo vc
        WHERE
            vc.fk_conta = cc.id_conta
            AND vc.status_venda = 'Confirmada'
    )
    WHERE cc.id_conta = v_conta;
END
$$;

COMMIT;
