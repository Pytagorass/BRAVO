-- ===================================================================
-- Modulo de consumo: restaurante, bar e lojinha
-- Projeto: BRAVO
--
-- Como executar:
--   psql -U postgres -d Barco_Hotel -f scripts/postgres/003_modulo_consumo.sql
--
-- Observacao:
--   O script e idempotente para facilitar execucoes repetidas no ambiente local.
-- ===================================================================

BEGIN;

-- -------------------------------------------------------------------
-- 1. Tipos enumerados
-- -------------------------------------------------------------------
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'tipo_categoria_consumo_enum') THEN
        CREATE TYPE tipo_categoria_consumo_enum AS ENUM ('Restaurante', 'Lojinha', 'Outros');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'status_conta_consumo_enum') THEN
        CREATE TYPE status_conta_consumo_enum AS ENUM ('Aberta', 'Fechada', 'Cancelada');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'status_venda_consumo_enum') THEN
        CREATE TYPE status_venda_consumo_enum AS ENUM ('Confirmada', 'Cancelada');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'tipo_movimento_estoque_enum') THEN
        CREATE TYPE tipo_movimento_estoque_enum AS ENUM ('Entrada', 'Saida', 'Ajuste', 'Cancelamento');
    END IF;
END
$$;

-- -------------------------------------------------------------------
-- 2. Cadastros de produto
-- -------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS categoria_produto (
    id_categoria SERIAL PRIMARY KEY,
    nome_categoria VARCHAR(100) NOT NULL,
    tipo_categoria tipo_categoria_consumo_enum NOT NULL,
    ativo status_ativo_enum NOT NULL DEFAULT 'Ativo',
    dt_criacao TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_categoria_produto_nome_tipo UNIQUE (nome_categoria, tipo_categoria)
);

CREATE TABLE IF NOT EXISTS produto (
    id_produto SERIAL PRIMARY KEY,
    fk_categoria INTEGER NOT NULL,
    nome_produto VARCHAR(120) NOT NULL,
    descricao TEXT,
    preco_atual DECIMAL(10, 2) NOT NULL CHECK (preco_atual >= 0),
    controla_estoque BOOLEAN NOT NULL DEFAULT FALSE,
    estoque_atual INTEGER NOT NULL DEFAULT 0 CHECK (estoque_atual >= 0),
    estoque_minimo INTEGER NOT NULL DEFAULT 0 CHECK (estoque_minimo >= 0),
    ativo status_ativo_enum NOT NULL DEFAULT 'Ativo',
    dt_criacao TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    dt_atualizacao TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_produto_categoria FOREIGN KEY (fk_categoria)
        REFERENCES categoria_produto(id_categoria) ON DELETE RESTRICT,
    CONSTRAINT uq_produto_categoria_nome UNIQUE (fk_categoria, nome_produto),
    CONSTRAINT chk_produto_estoque_controlado CHECK (
        controla_estoque = TRUE OR estoque_atual = 0
    )
);

-- -------------------------------------------------------------------
-- 3. Conta de consumo por reserva
-- -------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS conta_consumo (
    id_conta SERIAL PRIMARY KEY,
    fk_reserva INTEGER NOT NULL,
    total_acumulado DECIMAL(10, 2) NOT NULL DEFAULT 0.00 CHECK (total_acumulado >= 0),
    status_conta status_conta_consumo_enum NOT NULL DEFAULT 'Aberta',
    dt_abertura TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    dt_fechamento TIMESTAMP WITH TIME ZONE,
    CONSTRAINT fk_conta_consumo_reserva FOREIGN KEY (fk_reserva)
        REFERENCES reserva(id_reserva) ON DELETE CASCADE,
    CONSTRAINT uq_conta_consumo_reserva UNIQUE (fk_reserva),
    CONSTRAINT chk_conta_consumo_fechamento CHECK (
        (status_conta = 'Fechada' AND dt_fechamento IS NOT NULL)
        OR status_conta <> 'Fechada'
    )
);

-- -------------------------------------------------------------------
-- 4. Vendas e itens de consumo
-- -------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS venda_consumo (
    id_venda SERIAL PRIMARY KEY,
    fk_conta INTEGER NOT NULL,
    fk_reserva INTEGER NOT NULL,
    fk_usuario INTEGER NOT NULL,
    origem tipo_categoria_consumo_enum NOT NULL,
    status_venda status_venda_consumo_enum NOT NULL DEFAULT 'Confirmada',
    observacao TEXT,
    total_venda DECIMAL(10, 2) NOT NULL DEFAULT 0.00 CHECK (total_venda >= 0),
    dt_criacao TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    dt_cancelamento TIMESTAMP WITH TIME ZONE,
    CONSTRAINT fk_venda_consumo_conta FOREIGN KEY (fk_conta)
        REFERENCES conta_consumo(id_conta) ON DELETE CASCADE,
    CONSTRAINT fk_venda_consumo_reserva FOREIGN KEY (fk_reserva)
        REFERENCES reserva(id_reserva) ON DELETE RESTRICT,
    CONSTRAINT fk_venda_consumo_usuario FOREIGN KEY (fk_usuario)
        REFERENCES usuario(id_usuario) ON DELETE RESTRICT,
    CONSTRAINT chk_venda_cancelamento CHECK (
        (status_venda = 'Cancelada' AND dt_cancelamento IS NOT NULL)
        OR status_venda <> 'Cancelada'
    )
);

CREATE TABLE IF NOT EXISTS item_venda_consumo (
    id_item SERIAL PRIMARY KEY,
    fk_venda INTEGER NOT NULL,
    fk_produto INTEGER NOT NULL,
    quantidade INTEGER NOT NULL CHECK (quantidade > 0),
    valor_unitario DECIMAL(10, 2) NOT NULL CHECK (valor_unitario >= 0),
    subtotal DECIMAL(10, 2) NOT NULL CHECK (subtotal >= 0),
    observacao TEXT,
    dt_criacao TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_item_venda_consumo_venda FOREIGN KEY (fk_venda)
        REFERENCES venda_consumo(id_venda) ON DELETE CASCADE,
    CONSTRAINT fk_item_venda_consumo_produto FOREIGN KEY (fk_produto)
        REFERENCES produto(id_produto) ON DELETE RESTRICT
);

-- -------------------------------------------------------------------
-- 5. Estoque
-- -------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS movimento_estoque (
    id_movimento SERIAL PRIMARY KEY,
    fk_produto INTEGER NOT NULL,
    fk_usuario INTEGER NOT NULL,
    fk_item_venda INTEGER,
    tipo_movimento tipo_movimento_estoque_enum NOT NULL,
    quantidade INTEGER NOT NULL CHECK (quantidade > 0),
    estoque_anterior INTEGER NOT NULL CHECK (estoque_anterior >= 0),
    estoque_posterior INTEGER NOT NULL CHECK (estoque_posterior >= 0),
    observacao TEXT,
    dt_criacao TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_movimento_estoque_produto FOREIGN KEY (fk_produto)
        REFERENCES produto(id_produto) ON DELETE RESTRICT,
    CONSTRAINT fk_movimento_estoque_usuario FOREIGN KEY (fk_usuario)
        REFERENCES usuario(id_usuario) ON DELETE RESTRICT,
    CONSTRAINT fk_movimento_estoque_item FOREIGN KEY (fk_item_venda)
        REFERENCES item_venda_consumo(id_item) ON DELETE SET NULL
);

-- -------------------------------------------------------------------
-- 6. Indices
-- -------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_categoria_produto_tipo ON categoria_produto(tipo_categoria);
CREATE INDEX IF NOT EXISTS idx_categoria_produto_ativo ON categoria_produto(ativo);
CREATE INDEX IF NOT EXISTS idx_produto_categoria ON produto(fk_categoria);
CREATE INDEX IF NOT EXISTS idx_produto_ativo ON produto(ativo);
CREATE INDEX IF NOT EXISTS idx_conta_consumo_reserva ON conta_consumo(fk_reserva);
CREATE INDEX IF NOT EXISTS idx_conta_consumo_status ON conta_consumo(status_conta);
CREATE INDEX IF NOT EXISTS idx_venda_consumo_conta ON venda_consumo(fk_conta);
CREATE INDEX IF NOT EXISTS idx_venda_consumo_reserva ON venda_consumo(fk_reserva);
CREATE INDEX IF NOT EXISTS idx_venda_consumo_origem ON venda_consumo(origem);
CREATE INDEX IF NOT EXISTS idx_item_venda_consumo_venda ON item_venda_consumo(fk_venda);
CREATE INDEX IF NOT EXISTS idx_item_venda_consumo_produto ON item_venda_consumo(fk_produto);
CREATE INDEX IF NOT EXISTS idx_movimento_estoque_produto ON movimento_estoque(fk_produto);
CREATE INDEX IF NOT EXISTS idx_movimento_estoque_item ON movimento_estoque(fk_item_venda);

-- -------------------------------------------------------------------
-- 7. Dados iniciais
-- -------------------------------------------------------------------
INSERT INTO categoria_produto (nome_categoria, tipo_categoria)
VALUES
    ('Comidas', 'Restaurante'),
    ('Bebidas', 'Restaurante'),
    ('Lembrancas', 'Lojinha'),
    ('Vestuarios', 'Lojinha')
ON CONFLICT (nome_categoria, tipo_categoria) DO NOTHING;

COMMIT;
