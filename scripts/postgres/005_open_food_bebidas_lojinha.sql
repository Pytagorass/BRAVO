-- ===================================================================
-- Ajuste de consumo para pacote open food
-- Projeto: BRAVO
--
-- Regra de negocio:
--   Alimentacao esta inclusa no pacote (open food), portanto nao deve
--   ser vendida como item avulso. O consumo cobrado fica restrito a
--   bebidas e produtos da lojinha.
--
-- Como executar:
--   psql -U postgres -d Barco_Hotel -f scripts/postgres/005_open_food_bebidas_lojinha.sql
--
-- Observacao:
--   Idempotente. Remove itens de comida de vendas confirmadas e inativa
--   categorias/produtos de comida no cadastro de consumo.
-- ===================================================================

BEGIN;

-- Garante que as categorias vendaveis continuem disponiveis.
INSERT INTO categoria_produto (nome_categoria, tipo_categoria, ativo)
VALUES
    ('Bebidas', 'Restaurante', 'Ativo'),
    ('Lembrancas', 'Lojinha', 'Ativo'),
    ('Vestuarios', 'Lojinha', 'Ativo'),
    ('Utilidades', 'Lojinha', 'Ativo'),
    ('Pesca', 'Lojinha', 'Ativo')
ON CONFLICT (nome_categoria, tipo_categoria) DO UPDATE
SET ativo = EXCLUDED.ativo;

-- Inativa categorias de alimentacao que nao sao vendidas separadamente.
UPDATE categoria_produto
SET ativo = 'Inativo'
WHERE
    tipo_categoria = 'Restaurante'
    AND nome_categoria <> 'Bebidas';

-- Inativa produtos de alimentacao avulsa.
UPDATE produto p
SET
    ativo = 'Inativo',
    dt_atualizacao = NOW()
FROM categoria_produto cp
WHERE
    cp.id_categoria = p.fk_categoria
    AND cp.tipo_categoria = 'Restaurante'
    AND cp.nome_categoria <> 'Bebidas';

-- Remove itens de comida criados antes da regra open food.
DO $$
DECLARE
    item_food RECORD;
    estoque_atual_produto INTEGER;
BEGIN
    FOR item_food IN
        SELECT
            ivc.id_item,
            ivc.fk_produto,
            ivc.quantidade,
            p.controla_estoque
        FROM item_venda_consumo ivc
        JOIN venda_consumo vc ON vc.id_venda = ivc.fk_venda
        JOIN produto p ON p.id_produto = ivc.fk_produto
        JOIN categoria_produto cp ON cp.id_categoria = p.fk_categoria
        WHERE
            vc.status_venda = 'Confirmada'
            AND cp.tipo_categoria = 'Restaurante'
            AND cp.nome_categoria <> 'Bebidas'
    LOOP
        IF item_food.controla_estoque THEN
            SELECT estoque_atual
            INTO estoque_atual_produto
            FROM produto
            WHERE id_produto = item_food.fk_produto
            FOR UPDATE;

            UPDATE produto
            SET
                estoque_atual = estoque_atual_produto + item_food.quantidade,
                dt_atualizacao = NOW()
            WHERE id_produto = item_food.fk_produto;
        END IF;

        DELETE FROM movimento_estoque
        WHERE fk_item_venda = item_food.id_item;

        DELETE FROM item_venda_consumo
        WHERE id_item = item_food.id_item;
    END LOOP;
END
$$;

-- Recalcula totais de vendas e contas apos remover itens de comida.
UPDATE venda_consumo vc
SET total_venda = COALESCE((
    SELECT SUM(ivc.subtotal)
    FROM item_venda_consumo ivc
    WHERE ivc.fk_venda = vc.id_venda
), 0.00)
WHERE vc.status_venda = 'Confirmada';

DELETE FROM venda_consumo vc
WHERE
    vc.status_venda = 'Confirmada'
    AND NOT EXISTS (
        SELECT 1
        FROM item_venda_consumo ivc
        WHERE ivc.fk_venda = vc.id_venda
    );

UPDATE conta_consumo cc
SET total_acumulado = COALESCE((
    SELECT SUM(vc.total_venda)
    FROM venda_consumo vc
    WHERE
        vc.fk_conta = cc.id_conta
        AND vc.status_venda = 'Confirmada'
), 0.00);

COMMIT;
