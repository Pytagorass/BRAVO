-- =================================================================
-- 1. CRIAÇÃO DOS TIPOS ENUMERADOS (ENUMs)
-- =================================================================

CREATE TYPE tipo_usuario_enum AS ENUM (
    'Recepcionista',
    'Gerente',
    'Agente'
);

CREATE TYPE status_ativo_enum AS ENUM (
    'Ativo',
    'Inativo'
);

CREATE TYPE tipo_quarto_enum AS ENUM (
    'Solteiro',
    'Casal',
    'Triplo'
);

CREATE TYPE status_quarto_enum AS ENUM (
    'Disponível',
    'Manutenção'
);

CREATE TYPE status_reserva_enum AS ENUM (
    'Agendada',    -- Amarelo no protótipo (Reserva)
    'Ativa',       -- Verde no protótipo (Check-in feito)
    'Concluída',   -- (Check-out feito, opcional mas recomendado)
    'Cancelada'    -- Vermelho no protótipo
);

CREATE TYPE status_pagamento_enum AS ENUM (
    'Pendente',    -- Ícone "Pendente"
    'Em Partes',   -- Ícone "Em partes"
    'Pago',        -- (Ícone de "Pago", não estava no protótipo mas é necessário)
    'Cancelado'    -- Ícone "Cancelado"
);

CREATE TYPE tipo_hospede_enum AS ENUM (
    'Titular',
    'Acompanhante',
    'Criança'
);


-- =================================================================
-- 2. TABELAS DE ENTIDADES PRINCIPAIS
-- =================================================================

-- Tabela de Usuários do Sistema (Funcionários)
CREATE TABLE usuario (
    id_usuario SERIAL PRIMARY KEY,
    nome_usuario VARCHAR(100) NOT NULL,
    email_usuario VARCHAR(100) NOT NULL UNIQUE,
    senha VARCHAR(255) NOT NULL, -- Armazenará o hash da senha (ex: bcrypt)
    tipo_usuario tipo_usuario_enum NOT NULL,
    ativo status_ativo_enum NOT NULL DEFAULT 'Ativo'
);

-- Tabela de Hóspedes (Clientes)
CREATE TABLE hospede (
    id_hospede SERIAL PRIMARY KEY,
    nome_hospede VARCHAR(100) NOT NULL,
    email_hospede VARCHAR(100) NOT NULL,
    telefone VARCHAR(30),
    pais_origem VARCHAR(50) NOT NULL,
    passaporte VARCHAR(30) NULL,
    cpf VARCHAR(14) NULL,

    -- Restrição de Integridade (baseada no protótipo):
    -- Se for do Brasil, CPF é obrigatório.
    -- Se for de outro país, Passaporte é obrigatório.
    CONSTRAINT chk_documento_pais CHECK (
        (pais_origem = 'Brasil' AND cpf IS NOT NULL) OR
        (pais_origem != 'Brasil' AND passaporte IS NOT NULL)
    )
);

-- Tabela de Quartos (Inventário)
CREATE TABLE quarto (
    id_quarto SERIAL PRIMARY KEY,
    numero VARCHAR(10) NOT NULL UNIQUE, -- "Quarto 01", "Suíte Master", etc.
    tipo_quarto tipo_quarto_enum NOT NULL,
    valor_diaria DECIMAL(10, 2) NOT NULL CHECK (valor_diaria >= 0),
    status_quarto status_quarto_enum NOT NULL DEFAULT 'Disponível'
);


-- =================================================================
-- 3. TABELAS DE TRANSAÇÕES
-- =================================================================

-- Tabela de Reservas
CREATE TABLE reserva (
    id_reserva SERIAL PRIMARY KEY,
    dt_criacao TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    valor_total DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    observacao_reserva TEXT,
    forma_pagamento VARCHAR(50), -- Ex: 'Cartão de Crédito', 'Pix', 'Dinheiro'
    
    status_reserva status_reserva_enum NOT NULL DEFAULT 'Agendada',
    status_pagamento status_pagamento_enum NOT NULL DEFAULT 'Pendente',
    
    -- Chave Estrangeira: Quem criou a reserva no sistema
    fk_usuario INTEGER NOT NULL,
    CONSTRAINT fk_usuario_reserva
        FOREIGN KEY (fk_usuario)
        REFERENCES usuario(id_usuario)
        ON DELETE RESTRICT -- Não permite deletar um usuário que fez reservas
);

-- =================================================================
-- 4. TABELAS ASSOCIATIVAS
-- =================================================================

-- Tabela Associativa: Hóspedes de uma Reserva (N:M)
CREATE TABLE reserva_hospede (
    id_reserva_hospede SERIAL PRIMARY KEY,
    fk_reserva INTEGER NOT NULL,
    fk_hospede INTEGER NOT NULL,
    tipo_hospede tipo_hospede_enum NOT NULL,

    -- Chaves Estrangeiras
    CONSTRAINT fk_reserva_hospede_reserva
        FOREIGN KEY (fk_reserva)
        REFERENCES reserva(id_reserva)
        ON DELETE CASCADE, -- Se a reserva for deletada, remove os vínculos
    
    CONSTRAINT fk_reserva_hospede_hospede
        FOREIGN KEY (fk_hospede)
        REFERENCES hospede(id_hospede)
        ON DELETE RESTRICT, -- Não deixa deletar um hóspede vinculado a uma reserva
        
    -- Garante que um mesmo hóspede não seja adicionado 2x na MESMA reserva
    UNIQUE (fk_reserva, fk_hospede)
);

-- Tabela Associativa: Quartos de uma Reserva (N:M)
-- Esta é a tabela principal para o Gantt Chart.
CREATE TABLE reserva_quarto (
    id_reserva_quarto SERIAL PRIMARY KEY,
    
    fk_reserva INTEGER NOT NULL,
    fk_quarto INTEGER NOT NULL,
    
    checkin DATE NOT NULL,
    checkout DATE NOT NULL,
    
    -- "Congela" o valor da diária no momento da reserva
    valor_diaria_cobrado DECIMAL(10, 2) NOT NULL, 
    desconto DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    
    -- Chaves Estrangeiras
    CONSTRAINT fk_reserva_quarto_reserva
        FOREIGN KEY (fk_reserva)
        REFERENCES reserva(id_reserva)
        ON DELETE CASCADE,
    
    CONSTRAINT fk_reserva_quarto_quarto
        FOREIGN KEY (fk_quarto)
        REFERENCES quarto(id_quarto)
        ON DELETE RESTRICT,
        
    -- Restrição de Integridade: Data de checkout deve ser após o checkin
    CONSTRAINT chk_datas_validas CHECK (checkout > checkin)
);

-- =================================================================
-- 5. CRIAÇÃO DE ÍNDICES (Otimização de Consultas)
-- Cria índices B-Tree nas colunas de Chave Estrangeira (FK)
-- para acelerar massivamente as consultas com JOINs.
-- =================================================================

CREATE INDEX idx_reserva_fk_usuario ON reserva(fk_usuario);
CREATE INDEX idx_reserva_hospede_fk_reserva ON reserva_hospede(fk_reserva);
CREATE INDEX idx_reserva_hospede_fk_hospede ON reserva_hospede(fk_hospede);
CREATE INDEX idx_reserva_quarto_fk_reserva ON reserva_quarto(fk_reserva);
CREATE INDEX idx_reserva_quarto_fk_quarto ON reserva_quarto(fk_quarto);

-- Índice crucial para a consulta de Overbooking (OVERLAPS)
CREATE INDEX idx_reserva_quarto_datas ON reserva_quarto(checkin, checkout);



-- Alteração na Tabela Hospedes:
/* Adiciona a coluna 'ativo' na tabela de hóspedes.
  Usamos o 'status_ativo_enum' que você já criou para a tabela 'usuario'.
*/
ALTER TABLE hospede
ADD COLUMN ativo status_ativo_enum NOT NULL DEFAULT 'Ativo';

/* (Opcional, mas recomendado)
  Cria um índice para otimizar a busca por clientes ativos.
*/
CREATE INDEX idx_hospede_ativo ON hospede(ativo);

-- 1. Adiciona uma coluna 'nome_provisorio' na tabela de reserva.
-- Esta coluna vai guardar o nome da "Agência" ou "Grupo".
ALTER TABLE reserva
ADD COLUMN nome_provisorio VARCHAR(150) NULL;

-- =================================================================
-- 2. IMPLEMENTAÇÃO DA REGRA DE NEGÓCIO (TITULAR OU NOME)
-- =================================================================

-- 🎓 PASSO 2.1: A FUNÇÃO DE GATILHO
-- Esta função será chamada pelos nossos dois gatilhos.
-- Ela verifica se uma reserva específica está em um estado válido.
CREATE OR REPLACE FUNCTION check_reserva_valida()
RETURNS TRIGGER AS $$
DECLARE
    v_id_reserva INT;
    v_is_valid BOOLEAN;
BEGIN
    -- Determina qual ID de reserva verificar
    IF (TG_TABLE_NAME = 'reserva') THEN
        v_id_reserva := NEW.id_reserva;
    ELSIF (TG_TABLE_NAME = 'reserva_hospede') THEN
        v_id_reserva := OLD.fk_reserva;
    END IF;

    -- Verifica a lógica:
    -- A reserva é válida se (o nome provisório NÃO é nulo) OU (existe um titular)
    SELECT
        (r.nome_provisorio IS NOT NULL) OR
        (EXISTS (
            SELECT 1 FROM reserva_hospede rh
            WHERE rh.fk_reserva = r.id_reserva AND rh.tipo_hospede = 'Titular'
        ))
    INTO v_is_valid
    FROM reserva r
    WHERE r.id_reserva = v_id_reserva;

    -- Se não for válida, bloqueia a operação (INSERT/UPDATE/DELETE)
    IF NOT v_is_valid THEN
        RAISE EXCEPTION 'REGRA VIOLADA: A reserva (ID=%) deve ter um Nome Provisório (Agência) ou um Hóspede Titular associado.', v_id_reserva;
    END IF;

    -- Se chegou aqui, a operação é permitida
    IF (TG_OP = 'DELETE') THEN
        RETURN OLD;
    ELSE
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql;


-- 🎓 PASSO 2.2: O GATILHO NA TABELA 'reserva'
-- Vigia se alguém tentar APAGAR o nome provisório (UPDATE)
-- (Nota: O INSERT já é tratado pela sua view, mas isso garante.)
CREATE TRIGGER trg_check_reserva_on_update
AFTER UPDATE OF nome_provisorio ON reserva
FOR EACH ROW
WHEN (NEW.nome_provisorio IS NULL) -- Só roda se o novo nome for NULO
EXECUTE FUNCTION check_reserva_valida();


-- 🎓 PASSO 2.3: O GATILHO NA TABELA 'reserva_hospede'
-- Vigia se alguém EXCLUIR ou ALTERAR o último titular
CREATE TRIGGER trg_check_reserva_on_hospede_change
AFTER UPDATE OF tipo_hospede OR DELETE ON reserva_hospede
FOR EACH ROW
WHEN (OLD.tipo_hospede = 'Titular') -- Só roda se a linha antiga era de um Titular
EXECUTE FUNCTION check_reserva_valida();