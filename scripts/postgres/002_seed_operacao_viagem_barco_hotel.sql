-- ===================================================================
-- Seed de dados operacionais para barco-hotel
-- Projeto: Aguapei / BRAVO
--
-- Como executar:
--   psql -U postgres -d Barco_Hotel -f scripts/postgres/002_seed_operacao_viagem_barco_hotel.sql
--
-- Este script e idempotente:
--   - Pode ser executado mais de uma vez.
--   - Atualiza barcos/tipos existentes pelo nome.
--   - Cria roteiro diario apenas para reservas operacionais sem roteiro.
-- ===================================================================

BEGIN;

-- -------------------------------------------------------------------
-- 1. Barcos iniciais
-- Ajuste nomes/capacidades conforme sua operacao real.
-- -------------------------------------------------------------------
INSERT INTO barco (
    nome_barco,
    capacidade_pessoas,
    status_barco,
    observacao
)
VALUES
    (
        'Aguape I',
        12,
        'Disponível',
        'Barco principal para grupos completos e roteiros de pesca.'
    ),
    (
        'Aguape II',
        8,
        'Disponível',
        'Barco de apoio para grupos menores e roteiros personalizados.'
    ),
    (
        'Chalana Pantanal',
        16,
        'Disponível',
        'Embarcacao para passeios contemplativos e grupos maiores.'
    ),
    (
        'Barco de Apoio',
        6,
        'Disponível',
        'Embarcacao de suporte operacional, traslado e apoio logistico.'
    )
ON CONFLICT (nome_barco) DO UPDATE
SET
    capacidade_pessoas = EXCLUDED.capacidade_pessoas,
    status_barco = EXCLUDED.status_barco,
    observacao = EXCLUDED.observacao;

-- -------------------------------------------------------------------
-- 2. Tipos de passeio iniciais
-- -------------------------------------------------------------------
INSERT INTO tipo_passeio (
    nome_tipo,
    descricao,
    ativo
)
VALUES
    (
        'Pesca esportiva',
        'Roteiro focado em pesca esportiva com devolucao dos peixes, pontos combinados e suporte de guia.',
        'Ativo'
    ),
    (
        'Pesca tradicional',
        'Roteiro focado em pesca tradicional, conforme regras locais e combinados da operacao.',
        'Ativo'
    ),
    (
        'Contemplativo',
        'Passeio de descanso, navegacao, banho de rio e contemplacao da paisagem.',
        'Ativo'
    ),
    (
        'Observacao de aves',
        'Roteiro focado em observacao de aves, fauna, fotografia e paradas silenciosas.',
        'Ativo'
    ),
    (
        'Misto',
        'Roteiro personalizado combinando pesca, contemplacao, banho de rio e paradas especiais.',
        'Ativo'
    ),
    (
        'Corporativo',
        'Roteiro para grupos fechados, eventos, confraternizacoes e experiencias privativas.',
        'Ativo'
    ),
    (
        'Familia',
        'Roteiro leve para familias, com horarios flexiveis e atividades de baixa intensidade.',
        'Ativo'
    )
ON CONFLICT (nome_tipo) DO UPDATE
SET
    descricao = EXCLUDED.descricao,
    ativo = EXCLUDED.ativo;

-- -------------------------------------------------------------------
-- 3. Roteiro diario generico para reservas ja operacionais
--
-- Cria um dia de roteiro para reservas que:
--   - ja possuem tipo de passeio;
--   - ja possuem data de embarque/desembarque;
--   - ainda nao possuem roteiro em reserva_passeio_dia.
--
-- Se voce nao quiser gerar roteiros automaticos, comente este bloco.
-- -------------------------------------------------------------------
INSERT INTO reserva_passeio_dia (
    fk_reserva,
    fk_tipo_passeio,
    dia_viagem,
    data_passeio,
    titulo,
    local_previsto,
    observacao
)
SELECT
    r.id_reserva,
    r.fk_tipo_passeio,
    gs.dia_viagem,
    r.data_embarque + (gs.dia_viagem - 1),
    CASE
        WHEN gs.dia_viagem = 1 THEN 'Embarque e inicio da viagem'
        WHEN r.data_embarque + (gs.dia_viagem - 1) = r.data_desembarque THEN 'Retorno e desembarque'
        ELSE 'Dia de passeio'
    END AS titulo,
    CASE
        WHEN gs.dia_viagem = 1 THEN r.local_embarque
        WHEN r.data_embarque + (gs.dia_viagem - 1) = r.data_desembarque THEN r.local_desembarque
        ELSE NULL
    END AS local_previsto,
    'Roteiro gerado automaticamente pelo seed operacional.'
FROM reserva r
CROSS JOIN LATERAL generate_series(
    1,
    (r.data_desembarque - r.data_embarque + 1)
) AS gs(dia_viagem)
WHERE r.fk_tipo_passeio IS NOT NULL
  AND r.data_embarque IS NOT NULL
  AND r.data_desembarque IS NOT NULL
  AND r.data_desembarque >= r.data_embarque
  AND NOT EXISTS (
      SELECT 1
      FROM reserva_passeio_dia rpd
      WHERE rpd.fk_reserva = r.id_reserva
  )
ON CONFLICT (fk_reserva, dia_viagem) DO NOTHING;

COMMIT;
