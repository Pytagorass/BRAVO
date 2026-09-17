from django.db import migrations


FORWARD_SQL = """
CREATE EXTENSION IF NOT EXISTS btree_gist;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'usuario_email_usuario_key') THEN
        ALTER TABLE usuario ADD CONSTRAINT usuario_email_usuario_key UNIQUE (email_usuario);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'quarto_numero_key') THEN
        ALTER TABLE quarto ADD CONSTRAINT quarto_numero_key UNIQUE (numero);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'barco_nome_barco_key') THEN
        ALTER TABLE barco ADD CONSTRAINT barco_nome_barco_key UNIQUE (nome_barco);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'tipo_passeio_nome_tipo_key') THEN
        ALTER TABLE tipo_passeio ADD CONSTRAINT tipo_passeio_nome_tipo_key UNIQUE (nome_tipo);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'categoria_lavanderia_nome_categoria_key') THEN
        ALTER TABLE categoria_lavanderia ADD CONSTRAINT categoria_lavanderia_nome_categoria_key UNIQUE (nome_categoria);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'reserva_hospede_fk_reserva_fk_hospede_key') THEN
        ALTER TABLE reserva_hospede
            ADD CONSTRAINT reserva_hospede_fk_reserva_fk_hospede_key UNIQUE (fk_reserva, fk_hospede);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_rpd_reserva_dia') THEN
        ALTER TABLE reserva_passeio_dia ADD CONSTRAINT uq_rpd_reserva_dia UNIQUE (fk_reserva, dia_viagem);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_categoria_produto_nome_tipo') THEN
        ALTER TABLE categoria_produto
            ADD CONSTRAINT uq_categoria_produto_nome_tipo UNIQUE (nome_categoria, tipo_categoria);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_produto_categoria_nome') THEN
        ALTER TABLE produto ADD CONSTRAINT uq_produto_categoria_nome UNIQUE (fk_categoria, nome_produto);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_servico_lavanderia_categoria_nome') THEN
        ALTER TABLE servico_lavanderia
            ADD CONSTRAINT uq_servico_lavanderia_categoria_nome UNIQUE (fk_categoria, nome_servico);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_documento_pais') THEN
        ALTER TABLE hospede
            ADD CONSTRAINT chk_documento_pais CHECK (
                (pais_origem = 'Brasil' AND cpf IS NOT NULL)
                OR (pais_origem <> 'Brasil' AND passaporte IS NOT NULL)
            );
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_quarto_valor_diaria') THEN
        ALTER TABLE quarto ADD CONSTRAINT chk_quarto_valor_diaria CHECK (valor_diaria >= 0);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_barco_capacidade') THEN
        ALTER TABLE barco ADD CONSTRAINT chk_barco_capacidade CHECK (capacidade_pessoas > 0);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_reserva_datas_operacao_validas') THEN
        ALTER TABLE reserva
            ADD CONSTRAINT chk_reserva_datas_operacao_validas CHECK (
                data_embarque IS NULL
                OR data_desembarque IS NULL
                OR data_desembarque >= data_embarque
            );
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_reserva_barco_com_periodo') THEN
        ALTER TABLE reserva
            ADD CONSTRAINT chk_reserva_barco_com_periodo CHECK (
                fk_barco IS NULL
                OR (data_embarque IS NOT NULL AND data_desembarque IS NOT NULL)
            );
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_datas_validas') THEN
        ALTER TABLE reserva_quarto ADD CONSTRAINT chk_datas_validas CHECK (checkout > checkin);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_rpd_dia_viagem') THEN
        ALTER TABLE reserva_passeio_dia ADD CONSTRAINT chk_rpd_dia_viagem CHECK (dia_viagem > 0);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_produto_preco') THEN
        ALTER TABLE produto ADD CONSTRAINT chk_produto_preco CHECK (preco_atual >= 0);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_produto_estoque_atual') THEN
        ALTER TABLE produto ADD CONSTRAINT chk_produto_estoque_atual CHECK (estoque_atual >= 0);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_produto_estoque_minimo') THEN
        ALTER TABLE produto ADD CONSTRAINT chk_produto_estoque_minimo CHECK (estoque_minimo >= 0);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_produto_estoque_controlado') THEN
        ALTER TABLE produto
            ADD CONSTRAINT chk_produto_estoque_controlado CHECK (
                controla_estoque = TRUE OR estoque_atual = 0
            );
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_conta_consumo_total') THEN
        ALTER TABLE conta_consumo ADD CONSTRAINT chk_conta_consumo_total CHECK (total_acumulado >= 0);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_conta_consumo_fechamento') THEN
        ALTER TABLE conta_consumo
            ADD CONSTRAINT chk_conta_consumo_fechamento CHECK (
                (status_conta = 'Fechada' AND dt_fechamento IS NOT NULL)
                OR status_conta <> 'Fechada'
            );
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_venda_total') THEN
        ALTER TABLE venda_consumo ADD CONSTRAINT chk_venda_total CHECK (total_venda >= 0);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_venda_cancelamento') THEN
        ALTER TABLE venda_consumo
            ADD CONSTRAINT chk_venda_cancelamento CHECK (
                (status_venda = 'Cancelada' AND dt_cancelamento IS NOT NULL)
                OR status_venda <> 'Cancelada'
            );
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_item_venda_quantidade') THEN
        ALTER TABLE item_venda_consumo ADD CONSTRAINT chk_item_venda_quantidade CHECK (quantidade > 0);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_item_venda_valor_unitario') THEN
        ALTER TABLE item_venda_consumo ADD CONSTRAINT chk_item_venda_valor_unitario CHECK (valor_unitario >= 0);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_item_venda_subtotal') THEN
        ALTER TABLE item_venda_consumo ADD CONSTRAINT chk_item_venda_subtotal CHECK (subtotal >= 0);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_movimento_estoque_quantidade') THEN
        ALTER TABLE movimento_estoque ADD CONSTRAINT chk_movimento_estoque_quantidade CHECK (quantidade > 0);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_movimento_estoque_anterior') THEN
        ALTER TABLE movimento_estoque ADD CONSTRAINT chk_movimento_estoque_anterior CHECK (estoque_anterior >= 0);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_movimento_estoque_posterior') THEN
        ALTER TABLE movimento_estoque ADD CONSTRAINT chk_movimento_estoque_posterior CHECK (estoque_posterior >= 0);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_servico_lavanderia_preco') THEN
        ALTER TABLE servico_lavanderia ADD CONSTRAINT chk_servico_lavanderia_preco CHECK (preco_unitario >= 0);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_servico_lavanderia_prazo') THEN
        ALTER TABLE servico_lavanderia ADD CONSTRAINT chk_servico_lavanderia_prazo CHECK (prazo_horas > 0);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_ordem_lavanderia_total') THEN
        ALTER TABLE ordem_lavanderia ADD CONSTRAINT chk_ordem_lavanderia_total CHECK (total_ordem >= 0);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_ordem_lavanderia_entrega') THEN
        ALTER TABLE ordem_lavanderia
            ADD CONSTRAINT chk_ordem_lavanderia_entrega CHECK (
                (status_ordem = 'Entregue' AND dt_entrega IS NOT NULL)
                OR status_ordem <> 'Entregue'
            );
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_ordem_lavanderia_cancelamento') THEN
        ALTER TABLE ordem_lavanderia
            ADD CONSTRAINT chk_ordem_lavanderia_cancelamento CHECK (
                (status_ordem = 'Cancelado' AND dt_cancelamento IS NOT NULL)
                OR status_ordem <> 'Cancelado'
            );
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_item_ordem_lavanderia_quantidade') THEN
        ALTER TABLE item_ordem_lavanderia ADD CONSTRAINT chk_item_ordem_lavanderia_quantidade CHECK (quantidade > 0);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_item_ordem_lavanderia_valor_unitario') THEN
        ALTER TABLE item_ordem_lavanderia ADD CONSTRAINT chk_item_ordem_lavanderia_valor_unitario CHECK (valor_unitario >= 0);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_item_ordem_lavanderia_subtotal') THEN
        ALTER TABLE item_ordem_lavanderia ADD CONSTRAINT chk_item_ordem_lavanderia_subtotal CHECK (subtotal >= 0);
    END IF;

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
"""


REVERSE_SQL = """
ALTER TABLE reserva DROP CONSTRAINT IF EXISTS excl_reserva_barco_periodo;
ALTER TABLE item_ordem_lavanderia DROP CONSTRAINT IF EXISTS chk_item_ordem_lavanderia_subtotal;
ALTER TABLE item_ordem_lavanderia DROP CONSTRAINT IF EXISTS chk_item_ordem_lavanderia_valor_unitario;
ALTER TABLE item_ordem_lavanderia DROP CONSTRAINT IF EXISTS chk_item_ordem_lavanderia_quantidade;
ALTER TABLE ordem_lavanderia DROP CONSTRAINT IF EXISTS chk_ordem_lavanderia_cancelamento;
ALTER TABLE ordem_lavanderia DROP CONSTRAINT IF EXISTS chk_ordem_lavanderia_entrega;
ALTER TABLE ordem_lavanderia DROP CONSTRAINT IF EXISTS chk_ordem_lavanderia_total;
ALTER TABLE servico_lavanderia DROP CONSTRAINT IF EXISTS chk_servico_lavanderia_prazo;
ALTER TABLE servico_lavanderia DROP CONSTRAINT IF EXISTS chk_servico_lavanderia_preco;
ALTER TABLE movimento_estoque DROP CONSTRAINT IF EXISTS chk_movimento_estoque_posterior;
ALTER TABLE movimento_estoque DROP CONSTRAINT IF EXISTS chk_movimento_estoque_anterior;
ALTER TABLE movimento_estoque DROP CONSTRAINT IF EXISTS chk_movimento_estoque_quantidade;
ALTER TABLE item_venda_consumo DROP CONSTRAINT IF EXISTS chk_item_venda_subtotal;
ALTER TABLE item_venda_consumo DROP CONSTRAINT IF EXISTS chk_item_venda_valor_unitario;
ALTER TABLE item_venda_consumo DROP CONSTRAINT IF EXISTS chk_item_venda_quantidade;
ALTER TABLE venda_consumo DROP CONSTRAINT IF EXISTS chk_venda_cancelamento;
ALTER TABLE venda_consumo DROP CONSTRAINT IF EXISTS chk_venda_total;
ALTER TABLE conta_consumo DROP CONSTRAINT IF EXISTS chk_conta_consumo_fechamento;
ALTER TABLE conta_consumo DROP CONSTRAINT IF EXISTS chk_conta_consumo_total;
ALTER TABLE produto DROP CONSTRAINT IF EXISTS chk_produto_estoque_controlado;
ALTER TABLE produto DROP CONSTRAINT IF EXISTS chk_produto_estoque_minimo;
ALTER TABLE produto DROP CONSTRAINT IF EXISTS chk_produto_estoque_atual;
ALTER TABLE produto DROP CONSTRAINT IF EXISTS chk_produto_preco;
ALTER TABLE reserva_passeio_dia DROP CONSTRAINT IF EXISTS chk_rpd_dia_viagem;
ALTER TABLE reserva_quarto DROP CONSTRAINT IF EXISTS chk_datas_validas;
ALTER TABLE reserva DROP CONSTRAINT IF EXISTS chk_reserva_barco_com_periodo;
ALTER TABLE reserva DROP CONSTRAINT IF EXISTS chk_reserva_datas_operacao_validas;
ALTER TABLE barco DROP CONSTRAINT IF EXISTS chk_barco_capacidade;
ALTER TABLE quarto DROP CONSTRAINT IF EXISTS chk_quarto_valor_diaria;
ALTER TABLE hospede DROP CONSTRAINT IF EXISTS chk_documento_pais;
ALTER TABLE servico_lavanderia DROP CONSTRAINT IF EXISTS uq_servico_lavanderia_categoria_nome;
ALTER TABLE produto DROP CONSTRAINT IF EXISTS uq_produto_categoria_nome;
ALTER TABLE categoria_produto DROP CONSTRAINT IF EXISTS uq_categoria_produto_nome_tipo;
ALTER TABLE reserva_passeio_dia DROP CONSTRAINT IF EXISTS uq_rpd_reserva_dia;
ALTER TABLE reserva_hospede DROP CONSTRAINT IF EXISTS reserva_hospede_fk_reserva_fk_hospede_key;
ALTER TABLE categoria_lavanderia DROP CONSTRAINT IF EXISTS categoria_lavanderia_nome_categoria_key;
ALTER TABLE tipo_passeio DROP CONSTRAINT IF EXISTS tipo_passeio_nome_tipo_key;
ALTER TABLE barco DROP CONSTRAINT IF EXISTS barco_nome_barco_key;
ALTER TABLE quarto DROP CONSTRAINT IF EXISTS quarto_numero_key;
ALTER TABLE usuario DROP CONSTRAINT IF EXISTS usuario_email_usuario_key;
"""


class Migration(migrations.Migration):
    dependencies = [
        ('api', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(FORWARD_SQL, REVERSE_SQL),
    ]
