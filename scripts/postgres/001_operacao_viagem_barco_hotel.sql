-- ===================================================================
-- Operacao de viagem para barco-hotel
-- Projeto: Aguapei / BRAVO
--
-- Objetivo:
--   1. Cadastrar barcos.
--   2. Cadastrar tipos de passeio.
--   3. Ligar barco e passeio a reserva principal.
--   4. Permitir roteiro operacional por dia da viagem.
--
-- Como executar:
--   psql -U postgres -d Barco_Hotel -f scripts/postgres/001_operacao_viagem_barco_hotel.sql
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
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'status_barco_enum') THEN
        CREATE TYPE status_barco_enum AS ENUM ('Disponível', 'Manutenção', 'Bloqueado');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'status_operacional_enum') THEN
        CREATE TYPE status_operacional_enum AS ENUM ('A Preparar', 'Pronto', 'Em Viagem', 'Finalizado');
    END IF;
END
$$;

-- -------------------------------------------------------------------
-- 2. Cadastros operacionais
-- -------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS barco (
    id_barco SERIAL PRIMARY KEY,
    nome_barco VARCHAR(100) NOT NULL UNIQUE,
    capacidade_pessoas INTEGER NOT NULL CHECK (capacidade_pessoas > 0),
    status_barco status_barco_enum NOT NULL DEFAULT 'Disponível',
    observacao TEXT,
    dt_criacao TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS tipo_passeio (
    id_tipo_passeio SERIAL PRIMARY KEY,
    nome_tipo VARCHAR(100) NOT NULL UNIQUE,
    descricao TEXT,
    ativo status_ativo_enum NOT NULL DEFAULT 'Ativo',
    dt_criacao TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- -------------------------------------------------------------------
-- 3. Reserva principal passa a carregar dados da operacao da viagem
-- -------------------------------------------------------------------
ALTER TABLE reserva
    ADD COLUMN IF NOT EXISTS fk_barco INTEGER,
    ADD COLUMN IF NOT EXISTS fk_tipo_passeio INTEGER,
    ADD COLUMN IF NOT EXISTS data_embarque DATE,
    ADD COLUMN IF NOT EXISTS data_desembarque DATE,
    ADD COLUMN IF NOT EXISTS local_embarque VARCHAR(120),
    ADD COLUMN IF NOT EXISTS local_desembarque VARCHAR(120),
    ADD COLUMN IF NOT EXISTS status_operacional status_operacional_enum NOT NULL DEFAULT 'A Preparar',
    ADD COLUMN IF NOT EXISTS observacao_operacional TEXT;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_reserva_barco') THEN
        ALTER TABLE reserva
            ADD CONSTRAINT fk_reserva_barco
            FOREIGN KEY (fk_barco)
            REFERENCES barco(id_barco)
            ON DELETE RESTRICT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_reserva_tipo_passeio') THEN
        ALTER TABLE reserva
            ADD CONSTRAINT fk_reserva_tipo_passeio
            FOREIGN KEY (fk_tipo_passeio)
            REFERENCES tipo_passeio(id_tipo_passeio)
            ON DELETE RESTRICT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_reserva_datas_operacao_validas') THEN
        ALTER TABLE reserva
            ADD CONSTRAINT chk_reserva_datas_operacao_validas
            CHECK (
                data_embarque IS NULL
                OR data_desembarque IS NULL
                OR data_desembarque >= data_embarque
            );
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_reserva_barco_com_periodo') THEN
        ALTER TABLE reserva
            ADD CONSTRAINT chk_reserva_barco_com_periodo
            CHECK (
                fk_barco IS NULL
                OR (data_embarque IS NOT NULL AND data_desembarque IS NOT NULL)
            );
    END IF;
END
$$;

-- -------------------------------------------------------------------
-- 4. Roteiro operacional por dia da viagem
-- -------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS reserva_passeio_dia (
    id_reserva_passeio_dia SERIAL PRIMARY KEY,
    fk_reserva INTEGER NOT NULL,
    fk_tipo_passeio INTEGER,
    dia_viagem INTEGER NOT NULL CHECK (dia_viagem > 0),
    data_passeio DATE,
    titulo VARCHAR(120),
    local_previsto VARCHAR(120),
    observacao TEXT,
    CONSTRAINT fk_rpd_reserva FOREIGN KEY (fk_reserva)
        REFERENCES reserva(id_reserva) ON DELETE CASCADE,
    CONSTRAINT fk_rpd_tipo_passeio FOREIGN KEY (fk_tipo_passeio)
        REFERENCES tipo_passeio(id_tipo_passeio) ON DELETE RESTRICT,
    CONSTRAINT uq_rpd_reserva_dia UNIQUE (fk_reserva, dia_viagem)
);

-- -------------------------------------------------------------------
-- 5. Indices
-- -------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_barco_status ON barco(status_barco);
CREATE INDEX IF NOT EXISTS idx_tipo_passeio_ativo ON tipo_passeio(ativo);
CREATE INDEX IF NOT EXISTS idx_reserva_fk_barco ON reserva(fk_barco);
CREATE INDEX IF NOT EXISTS idx_reserva_fk_tipo_passeio ON reserva(fk_tipo_passeio);
CREATE INDEX IF NOT EXISTS idx_reserva_periodo_operacao ON reserva(data_embarque, data_desembarque);
CREATE INDEX IF NOT EXISTS idx_rpd_reserva ON reserva_passeio_dia(fk_reserva);
CREATE INDEX IF NOT EXISTS idx_rpd_tipo_passeio ON reserva_passeio_dia(fk_tipo_passeio);
CREATE INDEX IF NOT EXISTS idx_rpd_data_passeio ON reserva_passeio_dia(data_passeio);

-- -------------------------------------------------------------------
-- 6. Bloqueio de conflito de barco no mesmo periodo
-- -------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS btree_gist;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'excl_reserva_barco_periodo') THEN
        ALTER TABLE reserva
            ADD CONSTRAINT excl_reserva_barco_periodo
            EXCLUDE USING gist (
                fk_barco WITH =,
                (daterange(data_embarque, data_desembarque + 1, '[)')) WITH &&
            )
            WHERE (
                fk_barco IS NOT NULL
                AND data_embarque IS NOT NULL
                AND data_desembarque IS NOT NULL
                AND status_reserva <> 'Cancelada'
            );
    END IF;
END
$$;

-- -------------------------------------------------------------------
-- 7. Dados iniciais sugeridos
-- -------------------------------------------------------------------
INSERT INTO tipo_passeio (nome_tipo, descricao)
VALUES
    ('Pesca esportiva', 'Roteiro focado em pesca esportiva.'),
    ('Pesca tradicional', 'Roteiro focado em pesca tradicional.'),
    ('Contemplativo', 'Passeio de turismo, descanso e observacao da paisagem.'),
    ('Observacao de aves', 'Roteiro focado em observacao de aves e fauna.'),
    ('Misto', 'Roteiro personalizado com mais de uma atividade.')
ON CONFLICT (nome_tipo) DO NOTHING;

COMMIT;
