from decimal import Decimal

from django.db.models import Prefetch
from django.utils import timezone

from ..models import (
    ContaConsumo,
    ItemOrdemLavanderia,
    ItemVendaConsumo,
    OrdemLavanderia,
    Reserva,
    ReservaQuarto,
    VendaConsumo,
)


def _decimal_to_float(value):
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    return float(value or 0)


def _date_to_iso(value):
    return value.isoformat() if value else None


def _datetime_to_iso(value):
    if not value:
        return None
    return timezone.localtime(value).isoformat() if timezone.is_aware(value) else value.isoformat()


def _conta_da_reserva(reserva):
    try:
        return reserva.conta_consumo
    except ContaConsumo.DoesNotExist:
        return None


def _primeiro_quarto(reserva):
    quartos = list(reserva.quartos_reservados.all())
    return quartos[0] if quartos else None


def _checkout_previsto(reserva, reserva_quarto):
    return reserva_quarto.checkout if reserva_quarto else reserva.data_desembarque


def _dias_ate_checkout(checkout):
    if not checkout:
        return None
    return (checkout - timezone.localdate()).days


def _lancamentos_vendas(conta):
    lancamentos = []
    totais = {
        'bebidas': Decimal('0.00'),
        'lojinha': Decimal('0.00'),
    }

    for venda in conta.vendas.all():
        origem = venda.origem or 'Outros'
        if venda.status_venda != 'Confirmada':
            continue

        for item in venda.itens.all():
            categoria = 'Bebidas' if origem == 'Restaurante' else origem
            valor = item.subtotal or Decimal('0.00')
            if categoria == 'Bebidas':
                totais['bebidas'] += valor
            elif categoria == 'Lojinha':
                totais['lojinha'] += valor

            lancamentos.append(
                {
                    'id': f'venda-{venda.id_venda}-item-{item.id_item}',
                    'tipo': categoria,
                    'descricao': item.produto.nome_produto if item.produto else 'Produto',
                    'quantidade': item.quantidade,
                    'valor_unitario': _decimal_to_float(item.valor_unitario),
                    'subtotal': _decimal_to_float(valor),
                    'status': venda.status_venda,
                    'observacao': item.observacao or venda.observacao,
                    'usuario': venda.usuario.nome_usuario if venda.usuario else None,
                    'data_lancamento': _datetime_to_iso(item.dt_criacao or venda.dt_criacao),
                }
            )

    return lancamentos, totais


def _lancamentos_lavanderia(conta):
    lancamentos = []
    total = Decimal('0.00')

    for ordem in conta.ordens_lavanderia.all():
        if ordem.status_ordem == 'Cancelado':
            continue

        for item in ordem.itens.all():
            valor = item.subtotal or Decimal('0.00')
            total += valor
            lancamentos.append(
                {
                    'id': f'lavanderia-{ordem.id_ordem}-item-{item.id_item}',
                    'tipo': 'Lavanderia',
                    'descricao': item.servico.nome_servico if item.servico else 'Servico',
                    'quantidade': item.quantidade,
                    'valor_unitario': _decimal_to_float(item.valor_unitario),
                    'subtotal': _decimal_to_float(valor),
                    'status': ordem.status_ordem,
                    'observacao': item.observacao or ordem.observacao,
                    'usuario': ordem.usuario.nome_usuario if ordem.usuario else None,
                    'data_lancamento': _datetime_to_iso(item.dt_criacao or ordem.dt_criacao),
                }
            )

    return lancamentos, total


def _montar_conta_em_bordo(reserva):
    conta = _conta_da_reserva(reserva)
    reserva_quarto = _primeiro_quarto(reserva)
    checkout = _checkout_previsto(reserva, reserva_quarto)

    if conta:
        lancamentos_venda, totais_venda = _lancamentos_vendas(conta)
        lancamentos_lavanderia, total_lavanderia = _lancamentos_lavanderia(conta)
        lancamentos = sorted(
            [*lancamentos_venda, *lancamentos_lavanderia],
            key=lambda item: item.get('data_lancamento') or '',
            reverse=True,
        )
        total_conta = conta.total_acumulado or Decimal('0.00')
        status_conta = conta.status_conta
    else:
        lancamentos = []
        totais_venda = {'bebidas': Decimal('0.00'), 'lojinha': Decimal('0.00')}
        total_lavanderia = Decimal('0.00')
        total_conta = Decimal('0.00')
        status_conta = 'Sem conta'

    quarto = reserva_quarto.quarto if reserva_quarto else None
    hospede = reserva.hospede_titular

    return {
        'id_reserva': reserva.id_reserva,
        'id_conta': conta.id_conta if conta else None,
        'hospede': hospede.nome_hospede if hospede else 'Nao informado',
        'email_hospede': hospede.email_hospede if hospede else None,
        'telefone_hospede': hospede.telefone if hospede else None,
        'quarto': quarto.numero if quarto else None,
        'tipo_quarto': quarto.tipo_quarto if quarto else None,
        'barco': reserva.barco.nome_barco if reserva.barco else None,
        'tipo_passeio': reserva.tipo_passeio.nome_tipo if reserva.tipo_passeio else None,
        'status_reserva': reserva.status_reserva,
        'status_operacional': reserva.status_operacional,
        'status_conta': status_conta,
        'checkin': _date_to_iso(reserva_quarto.checkin if reserva_quarto else reserva.data_embarque),
        'checkout': _date_to_iso(checkout),
        'dias_ate_checkout': _dias_ate_checkout(checkout),
        'dt_abertura': _datetime_to_iso(conta.dt_abertura) if conta else None,
        'dt_fechamento': _datetime_to_iso(conta.dt_fechamento) if conta else None,
        'total_acumulado': _decimal_to_float(total_conta),
        'totais': {
            'bebidas': _decimal_to_float(totais_venda['bebidas']),
            'lojinha': _decimal_to_float(totais_venda['lojinha']),
            'lavanderia': _decimal_to_float(total_lavanderia),
        },
        'quantidade_lancamentos': len(lancamentos),
        'ultimo_lancamento': lancamentos[0] if lancamentos else None,
        'lancamentos': lancamentos,
    }


def buscar_contas_em_bordo():
    vendas_queryset = (
        VendaConsumo.objects.filter(status_venda='Confirmada')
        .select_related('usuario')
        .prefetch_related(
            Prefetch(
                'itens',
                queryset=ItemVendaConsumo.objects.select_related(
                    'produto',
                    'produto__categoria',
                ).order_by('-dt_criacao', '-id_item'),
            )
        )
        .order_by('-dt_criacao', '-id_venda')
    )
    lavanderia_queryset = (
        OrdemLavanderia.objects.exclude(status_ordem='Cancelado')
        .select_related('usuario')
        .prefetch_related(
            Prefetch(
                'itens',
                queryset=ItemOrdemLavanderia.objects.select_related(
                    'servico',
                    'servico__categoria',
                ).order_by('-dt_criacao', '-id_item'),
            )
        )
        .order_by('-dt_criacao', '-id_ordem')
    )

    reservas = (
        Reserva.objects.filter(status_reserva='Ativa')
        .select_related('hospede_titular', 'barco', 'tipo_passeio', 'conta_consumo')
        .prefetch_related(
            Prefetch(
                'quartos_reservados',
                queryset=ReservaQuarto.objects.select_related('quarto').order_by('checkin', 'id_reserva_quarto'),
            ),
            Prefetch('conta_consumo__vendas', queryset=vendas_queryset),
            Prefetch('conta_consumo__ordens_lavanderia', queryset=lavanderia_queryset),
        )
        .order_by('data_desembarque', 'id_reserva')
    )

    contas = [_montar_conta_em_bordo(reserva) for reserva in reservas]

    total_aberto = sum(
        Decimal(str(conta['total_acumulado']))
        for conta in contas
        if conta['status_conta'] == 'Aberta'
    )
    total_fechado = sum(
        Decimal(str(conta['total_acumulado']))
        for conta in contas
        if conta['status_conta'] == 'Fechada'
    )
    checkouts_hoje = sum(1 for conta in contas if conta['dias_ate_checkout'] == 0)
    checkouts_proximos = sum(
        1
        for conta in contas
        if conta['dias_ate_checkout'] is not None and 0 <= conta['dias_ate_checkout'] <= 2
    )

    return {
        'resumo': {
            'clientes_em_bordo': len(contas),
            'contas_abertas': sum(1 for conta in contas if conta['status_conta'] == 'Aberta'),
            'contas_fechadas': sum(1 for conta in contas if conta['status_conta'] == 'Fechada'),
            'sem_conta': sum(1 for conta in contas if conta['status_conta'] == 'Sem conta'),
            'total_aberto': _decimal_to_float(total_aberto),
            'total_fechado': _decimal_to_float(total_fechado),
            'checkouts_hoje': checkouts_hoje,
            'checkouts_proximos': checkouts_proximos,
        },
        'contas': contas,
    }
