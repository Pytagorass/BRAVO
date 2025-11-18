-- ===================================================================
--  SCHEMA DO SISTEMA DE GERENCIAMENTO DO BARCO-HOTEL (Aguapeí)
-- ===================================================================

-- -------------------------------------------------------------------
-- 1. TIPOS ENUMERADOS
-- -------------------------------------------------------------------
CREATE TYPE tipo_usuario_enum AS ENUM ('Recepcionista', 'Gerente', 'Agente');
CREATE TYPE status_ativo_enum AS ENUM ('Ativo', 'Inativo');
CREATE TYPE tipo_quarto_enum AS ENUM ('Solteiro', 'Casal', 'Triplo');
CREATE TYPE status_quarto_enum AS ENUM ('Disponível', 'Manutenção');
CREATE TYPE status_reserva_enum AS ENUM ('Agendada', 'Ativa', 'Concluída', 'Cancelada');
CREATE TYPE status_pagamento_enum AS ENUM ('Pendente', 'Em Partes', 'Pago', 'Cancelado');


-- -------------------------------------------------------------------
-- 2. TABELAS PRINCIPAIS
-- -------------------------------------------------------------------
CREATE TABLE usuario (
    id_usuario SERIAL PRIMARY KEY,
    nome_usuario VARCHAR(100) NOT NULL,
    email_usuario VARCHAR(100) NOT NULL UNIQUE,
    senha VARCHAR(255) NOT NULL,
    tipo_usuario tipo_usuario_enum NOT NULL,
    ativo status_ativo_enum NOT NULL DEFAULT 'Ativo'
);

CREATE TABLE hospede (
    id_hospede SERIAL PRIMARY KEY,
    nome_hospede VARCHAR(100) NOT NULL,
    email_hospede VARCHAR(100) NOT NULL,
    telefone VARCHAR(30),
    pais_origem VARCHAR(50) NOT NULL,
    passaporte VARCHAR(30),
    cpf VARCHAR(14),
    ativo status_ativo_enum NOT NULL DEFAULT 'Ativo',
    CONSTRAINT chk_documento_pais CHECK (
        (pais_origem = 'Brasil' AND cpf IS NOT NULL) OR
        (pais_origem <> 'Brasil' AND passaporte IS NOT NULL)
    )
);

CREATE TABLE quarto (
    id_quarto SERIAL PRIMARY KEY,
    numero VARCHAR(10) NOT NULL UNIQUE,
    tipo_quarto tipo_quarto_enum NOT NULL,
    valor_diaria DECIMAL(10, 2) NOT NULL CHECK (valor_diaria >= 0),
    status_quarto status_quarto_enum NOT NULL DEFAULT 'Disponível'
);

CREATE TABLE reserva (
    id_reserva SERIAL PRIMARY KEY,
    dt_criacao TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    valor_total DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    observacao_reserva TEXT,
    fk_hospede_titular INTEGER NOT NULL,
    status_reserva status_reserva_enum NOT NULL DEFAULT 'Agendada',
    status_pagamento status_pagamento_enum NOT NULL DEFAULT 'Pendente',
    fk_usuario INTEGER NOT NULL,
    CONSTRAINT fk_reserva_usuario FOREIGN KEY (fk_usuario)
        REFERENCES usuario(id_usuario) ON DELETE RESTRICT,
    CONSTRAINT fk_reserva_titular FOREIGN KEY (fk_hospede_titular)
        REFERENCES hospede(id_hospede) ON DELETE RESTRICT
);


-- -------------------------------------------------------------------
-- 3. TABELAS ASSOCIATIVAS
-- -------------------------------------------------------------------
CREATE TABLE reserva_hospede (
    id_reserva_hospede SERIAL PRIMARY KEY,
    fk_reserva INTEGER NOT NULL,
    fk_hospede INTEGER NOT NULL,
    CONSTRAINT fk_rh_reserva FOREIGN KEY (fk_reserva)
        REFERENCES reserva(id_reserva) ON DELETE CASCADE,
    CONSTRAINT fk_rh_hospede FOREIGN KEY (fk_hospede)
        REFERENCES hospede(id_hospede) ON DELETE RESTRICT,
    UNIQUE (fk_reserva, fk_hospede)
);

CREATE TABLE reserva_quarto (
    id_reserva_quarto SERIAL PRIMARY KEY,
    fk_reserva INTEGER NOT NULL,
    fk_quarto INTEGER NOT NULL,
    checkin DATE NOT NULL,
    checkout DATE NOT NULL,
    valor_diaria_cobrado DECIMAL(10, 2) NOT NULL,
    desconto DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    CONSTRAINT fk_rq_reserva FOREIGN KEY (fk_reserva)
        REFERENCES reserva(id_reserva) ON DELETE CASCADE,
    CONSTRAINT fk_rq_quarto FOREIGN KEY (fk_quarto)
        REFERENCES quarto(id_quarto) ON DELETE RESTRICT,
    CONSTRAINT chk_datas_validas CHECK (checkout > checkin)
);


-- -------------------------------------------------------------------
-- 4. ÍNDICES AUXILIARES
-- -------------------------------------------------------------------
CREATE INDEX idx_usuario_email ON usuario(email_usuario);
CREATE INDEX idx_hospede_ativo ON hospede(ativo);
CREATE INDEX idx_reserva_fk_usuario ON reserva(fk_usuario);
CREATE INDEX idx_reserva_fk_titular ON reserva(fk_hospede_titular);
CREATE INDEX idx_reserva_hospede_reserva ON reserva_hospede(fk_reserva);
CREATE INDEX idx_reserva_hospede_hospede ON reserva_hospede(fk_hospede);
CREATE INDEX idx_reserva_quarto_reserva ON reserva_quarto(fk_reserva);
CREATE INDEX idx_reserva_quarto_quarto ON reserva_quarto(fk_quarto);
CREATE INDEX idx_reserva_quarto_periodo ON reserva_quarto(checkin, checkout);


