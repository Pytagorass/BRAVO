-- ===================================================================
-- Modulo de lavanderia por peca
-- Projeto: BRAVO
--
-- Regra de negocio:
--   A lavanderia atende apenas roupas pessoais dos turistas. Cama e banho
--   nao entram neste modulo.
--
-- Como executar:
--   psql -U postgres -d Barco_Hotel -f scripts/postgres/006_modulo_lavanderia.sql
--
-- Observacao:
--   Idempotente. Cria as tabelas, indices e dados iniciais de servicos.
-- ===================================================================

BEGIN;

-- -------------------------------------------------------------------
-- 1. Tipos enumerados
-- -------------------------------------------------------------------
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'status_ordem_lavanderia_enum') THEN
        CREATE TYPE status_ordem_lavanderia_enum AS ENUM (
            'Recebido',
            'Em Lavagem',
            'Pronto',
            'Entregue',
            'Cancelado'
        );
    END IF;
END
$$;

-- -------------------------------------------------------------------
-- 2. Catalogo de categorias e servicos
-- -------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS categoria_lavanderia (
    id_categoria SERIAL PRIMARY KEY,
    nome_categoria VARCHAR(100) NOT NULL UNIQUE,
    descricao TEXT,
    ativo status_ativo_enum NOT NULL DEFAULT 'Ativo',
    ordem_exibicao INTEGER NOT NULL DEFAULT 0,
    dt_criacao TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS servico_lavanderia (
    id_servico SERIAL PRIMARY KEY,
    fk_categoria INTEGER NOT NULL,
    nome_servico VARCHAR(120) NOT NULL,
    descricao TEXT,
    preco_unitario DECIMAL(10, 2) NOT NULL CHECK (preco_unitario >= 0),
    prazo_horas INTEGER NOT NULL DEFAULT 24 CHECK (prazo_horas > 0),
    ativo status_ativo_enum NOT NULL DEFAULT 'Ativo',
    dt_criacao TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    dt_atualizacao TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_servico_lavanderia_categoria FOREIGN KEY (fk_categoria)
        REFERENCES categoria_lavanderia(id_categoria) ON DELETE RESTRICT,
    CONSTRAINT uq_servico_lavanderia_categoria_nome UNIQUE (fk_categoria, nome_servico)
);

-- -------------------------------------------------------------------
-- 3. Ordens vinculadas a reserva e conta de consumo
-- -------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ordem_lavanderia (
    id_ordem SERIAL PRIMARY KEY,
    fk_conta INTEGER NOT NULL,
    fk_reserva INTEGER NOT NULL,
    fk_usuario INTEGER NOT NULL,
    status_ordem status_ordem_lavanderia_enum NOT NULL DEFAULT 'Recebido',
    observacao TEXT,
    total_ordem DECIMAL(10, 2) NOT NULL DEFAULT 0.00 CHECK (total_ordem >= 0),
    dt_recebimento TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    dt_previsao_entrega TIMESTAMP WITH TIME ZONE,
    dt_entrega TIMESTAMP WITH TIME ZONE,
    dt_cancelamento TIMESTAMP WITH TIME ZONE,
    dt_criacao TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_ordem_lavanderia_conta FOREIGN KEY (fk_conta)
        REFERENCES conta_consumo(id_conta) ON DELETE CASCADE,
    CONSTRAINT fk_ordem_lavanderia_reserva FOREIGN KEY (fk_reserva)
        REFERENCES reserva(id_reserva) ON DELETE RESTRICT,
    CONSTRAINT fk_ordem_lavanderia_usuario FOREIGN KEY (fk_usuario)
        REFERENCES usuario(id_usuario) ON DELETE RESTRICT,
    CONSTRAINT chk_ordem_lavanderia_entrega CHECK (
        (status_ordem = 'Entregue' AND dt_entrega IS NOT NULL)
        OR status_ordem <> 'Entregue'
    ),
    CONSTRAINT chk_ordem_lavanderia_cancelamento CHECK (
        (status_ordem = 'Cancelado' AND dt_cancelamento IS NOT NULL)
        OR status_ordem <> 'Cancelado'
    )
);

CREATE TABLE IF NOT EXISTS item_ordem_lavanderia (
    id_item SERIAL PRIMARY KEY,
    fk_ordem INTEGER NOT NULL,
    fk_servico INTEGER NOT NULL,
    quantidade INTEGER NOT NULL CHECK (quantidade > 0),
    valor_unitario DECIMAL(10, 2) NOT NULL CHECK (valor_unitario >= 0),
    subtotal DECIMAL(10, 2) NOT NULL CHECK (subtotal >= 0),
    observacao TEXT,
    dt_criacao TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_item_ordem_lavanderia_ordem FOREIGN KEY (fk_ordem)
        REFERENCES ordem_lavanderia(id_ordem) ON DELETE CASCADE,
    CONSTRAINT fk_item_ordem_lavanderia_servico FOREIGN KEY (fk_servico)
        REFERENCES servico_lavanderia(id_servico) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS historico_lavanderia_status (
    id_historico SERIAL PRIMARY KEY,
    fk_ordem INTEGER NOT NULL,
    status_anterior status_ordem_lavanderia_enum,
    status_novo status_ordem_lavanderia_enum NOT NULL,
    fk_usuario INTEGER NOT NULL,
    observacao TEXT,
    dt_alteracao TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_historico_lavanderia_ordem FOREIGN KEY (fk_ordem)
        REFERENCES ordem_lavanderia(id_ordem) ON DELETE CASCADE,
    CONSTRAINT fk_historico_lavanderia_usuario FOREIGN KEY (fk_usuario)
        REFERENCES usuario(id_usuario) ON DELETE RESTRICT
);

-- -------------------------------------------------------------------
-- 4. Indices
-- -------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_categoria_lavanderia_ativo ON categoria_lavanderia(ativo);
CREATE INDEX IF NOT EXISTS idx_servico_lavanderia_categoria ON servico_lavanderia(fk_categoria);
CREATE INDEX IF NOT EXISTS idx_servico_lavanderia_ativo ON servico_lavanderia(ativo);
CREATE INDEX IF NOT EXISTS idx_ordem_lavanderia_conta ON ordem_lavanderia(fk_conta);
CREATE INDEX IF NOT EXISTS idx_ordem_lavanderia_reserva ON ordem_lavanderia(fk_reserva);
CREATE INDEX IF NOT EXISTS idx_ordem_lavanderia_status ON ordem_lavanderia(status_ordem);
CREATE INDEX IF NOT EXISTS idx_item_ordem_lavanderia_ordem ON item_ordem_lavanderia(fk_ordem);
CREATE INDEX IF NOT EXISTS idx_item_ordem_lavanderia_servico ON item_ordem_lavanderia(fk_servico);
CREATE INDEX IF NOT EXISTS idx_historico_lavanderia_ordem ON historico_lavanderia_status(fk_ordem);

-- -------------------------------------------------------------------
-- 5. Dados iniciais: somente roupas pessoais dos turistas
-- -------------------------------------------------------------------
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
