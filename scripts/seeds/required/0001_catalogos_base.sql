-- ===================================================================
-- BRAVO - Seeds obrigatorios de catalogos base
--
-- Este arquivo e um fallback manual. O fluxo principal agora carrega
-- estes catalogos pela migration Django api.0003_seed_required_catalogs.
--
-- Dados aqui sao catalogos minimos para o sistema funcionar bem:
-- tipos de passeio, categorias vendaveis do open food e catalogo de
-- lavanderia por peca.
--
-- Nao coloque reservas, vendas ou dados demonstrativos neste arquivo.
-- ===================================================================

BEGIN;

INSERT INTO tipo_passeio (nome_tipo, descricao, ativo)
VALUES
    ('Pesca esportiva', 'Roteiro focado em pesca esportiva com devolucao dos peixes, pontos combinados e suporte de guia.', 'Ativo'),
    ('Pesca tradicional', 'Roteiro focado em pesca tradicional, conforme regras locais e combinados da operacao.', 'Ativo'),
    ('Contemplativo', 'Passeio de descanso, navegacao, banho de rio e contemplacao da paisagem.', 'Ativo'),
    ('Observacao de aves', 'Roteiro focado em observacao de aves, fauna, fotografia e paradas silenciosas.', 'Ativo'),
    ('Misto', 'Roteiro personalizado combinando pesca, contemplacao, banho de rio e paradas especiais.', 'Ativo'),
    ('Corporativo', 'Roteiro para grupos fechados, eventos, confraternizacoes e experiencias privativas.', 'Ativo'),
    ('Familia', 'Roteiro leve para familias, com horarios flexiveis e atividades de baixa intensidade.', 'Ativo')
ON CONFLICT (nome_tipo) DO UPDATE
SET
    descricao = EXCLUDED.descricao,
    ativo = EXCLUDED.ativo;

INSERT INTO categoria_produto (nome_categoria, tipo_categoria, ativo)
VALUES
    ('Bebidas', 'Restaurante', 'Ativo'),
    ('Lembrancas', 'Lojinha', 'Ativo'),
    ('Vestuarios', 'Lojinha', 'Ativo'),
    ('Utilidades', 'Lojinha', 'Ativo'),
    ('Pesca', 'Lojinha', 'Ativo')
ON CONFLICT (nome_categoria, tipo_categoria) DO UPDATE
SET ativo = EXCLUDED.ativo;

UPDATE categoria_produto
SET ativo = 'Inativo'
WHERE
    tipo_categoria = 'Restaurante'
    AND nome_categoria <> 'Bebidas';

INSERT INTO categoria_lavanderia (nome_categoria, descricao, ordem_exibicao, ativo)
VALUES
    ('Roupas leves', 'Pecas leves de uso diario dos turistas.', 10, 'Ativo'),
    ('Roupas pesadas', 'Pecas mais volumosas ou de tecido pesado.', 20, 'Ativo'),
    ('Roupas especiais', 'Pecas de pesca, praia ou acessorios pessoais.', 30, 'Ativo')
ON CONFLICT (nome_categoria) DO UPDATE
SET
    descricao = EXCLUDED.descricao,
    ordem_exibicao = EXCLUDED.ordem_exibicao,
    ativo = EXCLUDED.ativo;

INSERT INTO servico_lavanderia (
    fk_categoria,
    nome_servico,
    descricao,
    preco_unitario,
    prazo_horas,
    ativo
)
SELECT
    c.id_categoria,
    seed.nome_servico,
    seed.descricao,
    seed.preco_unitario,
    seed.prazo_horas,
    'Ativo'
FROM (
    VALUES
        ('Roupas leves', 'Camiseta', 'Lavagem de camiseta por peca.', 8.00, 24),
        ('Roupas leves', 'Camisa', 'Lavagem de camisa por peca.', 10.00, 24),
        ('Roupas leves', 'Regata', 'Lavagem de regata por peca.', 7.00, 24),
        ('Roupas leves', 'Short / Bermuda', 'Lavagem de short ou bermuda por peca.', 10.00, 24),
        ('Roupas leves', 'Roupa intima', 'Lavagem de roupa intima por peca.', 5.00, 24),
        ('Roupas leves', 'Meia', 'Lavagem de par de meias.', 4.00, 24),
        ('Roupas pesadas', 'Calca jeans', 'Lavagem de calca jeans por peca.', 16.00, 36),
        ('Roupas pesadas', 'Calca moletom', 'Lavagem de calca moletom por peca.', 14.00, 36),
        ('Roupas pesadas', 'Blusa de frio', 'Lavagem de blusa de frio por peca.', 18.00, 36),
        ('Roupas pesadas', 'Jaqueta', 'Lavagem de jaqueta por peca.', 22.00, 48),
        ('Roupas especiais', 'Camisa UV', 'Lavagem de camisa UV por peca.', 12.00, 24),
        ('Roupas especiais', 'Roupa de pesca', 'Lavagem de roupa de pesca por peca.', 15.00, 36),
        ('Roupas especiais', 'Chapeu / Bone', 'Lavagem de chapeu ou bone por peca.', 8.00, 24),
        ('Roupas especiais', 'Maio / Biquini / Sunga', 'Lavagem de roupa de banho pessoal por peca.', 7.00, 24)
) AS seed (nome_categoria, nome_servico, descricao, preco_unitario, prazo_horas)
JOIN categoria_lavanderia c ON c.nome_categoria = seed.nome_categoria
ON CONFLICT (fk_categoria, nome_servico) DO UPDATE
SET
    descricao = EXCLUDED.descricao,
    preco_unitario = EXCLUDED.preco_unitario,
    prazo_horas = EXCLUDED.prazo_horas,
    ativo = EXCLUDED.ativo,
    dt_atualizacao = NOW();

COMMIT;
