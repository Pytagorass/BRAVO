import 'package:bravo_restaurante/models/conta_consumo.dart';
import 'package:bravo_restaurante/models/lavanderia.dart';
import 'package:bravo_restaurante/models/reserva.dart';
import 'package:bravo_restaurante/mvvm/conta_consumo_viewmodel.dart';
import 'package:bravo_restaurante/mvvm/reserva_viewmodel.dart';
import 'package:bravo_restaurante/widgets/cores_app.dart';
import 'package:bravo_restaurante/widgets/consumo_card.dart';
import 'package:bravo_restaurante/widgets/alerta_informacoes_pagina.dart';
import 'package:bravo_restaurante/widgets/reserva_dropdown.dart';
import 'package:bravo_restaurante/widgets/total_card.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

String _formatarDataConta(DateTime? data) {
  if (data == null) return 'Data nao informada';

  final dataLocal = data.toLocal();
  String doisDigitos(int numero) => numero.toString().padLeft(2, '0');

  final dia = doisDigitos(dataLocal.day);
  final mes = doisDigitos(dataLocal.month);
  final hora = doisDigitos(dataLocal.hour);
  final minuto = doisDigitos(dataLocal.minute);

  return '$dia/$mes/${dataLocal.year} $hora:$minuto';
}

class ContaHospedeView extends StatefulWidget {
  const ContaHospedeView({super.key});

  @override
  State<ContaHospedeView> createState() => _ContaHospedeViewState();
}

class _ContaHospedeViewState extends State<ContaHospedeView> {
  // Reserva usada para buscar e exibir a conta de consumo.
  Reserva? reservaSelecionada;
  late final ContaConsumoViewModel _contaVM;

  @override
  void initState() {
    super.initState();
    _contaVM = context.read<ContaConsumoViewModel>();

    // A tela sempre começa listando as reservas abertas disponíveis.
    Future.microtask(() {
      // ignore: use_build_context_synchronously
      context.read<ReservaViewModel>().carregarReservasAbertas();
    });
  }

  @override
  void dispose() {
    // Garante que a próxima abertura da tela não herde a conta selecionada.
    _contaVM.limpar(notificar: false);
    super.dispose();
  }

  Future<void> _selecionarReserva(Reserva? reserva) async {
    // Ao trocar a reserva, a conta exibida precisa acompanhar a seleção.
    setState(() {
      reservaSelecionada = reserva;
    });

    if (reserva == null) {
      _contaVM.limpar();
      return;
    }

    await _contaVM.carregarContaDaReserva(reserva);
  }

  @override
  Widget build(BuildContext context) {
    // Observa reservas e conta para atualizar a tela conforme as buscas terminam.
    return Consumer2<ReservaViewModel, ContaConsumoViewModel>(
      builder: (context, reservaVM, contaVM, child) {
        return Scaffold(
          backgroundColor: Colors.white,
          appBar: AppBar(
            title: const Text(
              'Conta do Hospede',
              style: TextStyle(fontWeight: FontWeight.bold),
            ),
            backgroundColor: CoresApp.verdeEscuro,
            foregroundColor: Colors.white,
          ),
          body: reservaVM.isLoading
              ? const Center(child: CircularProgressIndicator())
              : RefreshIndicator(
                  onRefresh: () async {
                    // Pull-to-refresh recarrega a conta da reserva atual.
                    if (reservaSelecionada != null) {
                      await contaVM.carregarContaDaReserva(reservaSelecionada!);
                    }
                  },
                  child: ListView(
                    padding: const EdgeInsets.all(16),
                    children: [
                      // Aviso inicial explicando o objetivo desta consulta.
                      const AlertaInformacoesPagina(
                        message:
                            'Consulte lojinha, bebidas, lavanderia e total acumulado de uma reserva aberta.',
                      ),

                      const SizedBox(height: 16),

                      _buildReservaDropdown(reservaVM),
                      const SizedBox(height: 16),
                      // Abaixo do dropdown, a tela alterna entre loading, erro e detalhes.
                      if (contaVM.isLoading)
                        const Padding(
                          padding: EdgeInsets.all(24),
                          child: Center(child: CircularProgressIndicator()),
                        )
                      else if (contaVM.mensagemErro != null)
                        _MensagemCard(mensagem: contaVM.mensagemErro!)
                      else if (contaVM.conta != null)
                        _ContaDetalhes(conta: contaVM.conta!)
                      else
                        const _MensagemCard(
                          mensagem: 'Selecione uma reserva para ver a conta.',
                        ),
                    ],
                  ),
                ),
        );
      },
    );
  }

  Widget _buildReservaDropdown(ReservaViewModel reservaVM) {
    // Antes do dropdown, a tela trata erro ou ausência de reservas abertas.
    return ReservaDropdown(
      reservaVM: reservaVM,
      reservaSelecionada: reservaSelecionada,
      label: 'Reserva / Quarto',
      mensagemBuilder: (mensagem) => _MensagemCard(mensagem: mensagem),
      onChanged: (value) {
        // Trocar a reserva dispara nova busca da ContaConsumo.
        _selecionarReserva(value);
      },
    );
  }
}

class _ContaDetalhes extends StatelessWidget {
  final ContaConsumo conta;

  const _ContaDetalhes({required this.conta});

  @override
  Widget build(BuildContext context) {
    // Mostra o resumo financeiro e as origens de consumo da conta.
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        TotalCard(
          titulo: 'Conta ${conta.statusConta}',
          valor: conta.totalAcumulado,
          valorFontSize: 26,
        ),
        const SizedBox(height: 18),
        const Text(
          'Lojinha',
          style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
        ),
        const SizedBox(height: 8),
        if (conta.pedidos.isEmpty)
          const _MensagemCard(mensagem: 'Nenhum produto da lojinha registrado.')
        else
          ...conta.pedidos.map((pedido) => _PedidoCard(pedido: pedido)),
        const SizedBox(height: 18),
        const Text(
          'Bebidas',
          style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
        ),
        const SizedBox(height: 8),
        if (conta.bebidas.isEmpty)
          const _MensagemCard(mensagem: 'Nenhuma bebida lancada.')
        else
          ...conta.bebidas.map((bebida) => _BebidaCard(bebida: bebida)),
        const SizedBox(height: 18),
        const Text(
          'Lavanderia',
          style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
        ),
        const SizedBox(height: 8),
        if (conta.lavanderias.isEmpty)
          const _MensagemCard(mensagem: 'Nenhuma lavanderia lancada.')
        else
          ...conta.lavanderias.map((ordem) => _LavanderiaCard(ordem: ordem)),
      ],
    );
  }
}

class _PedidoCard extends StatelessWidget {
  final PedidoConta pedido;

  const _PedidoCard({required this.pedido});

  @override
  Widget build(BuildContext context) {
    // Card no mesmo padrao visual da tela Fechar Conta.
    final dataPedido = _formatarDataConta(pedido.createdAt);

    return ConsumoCard(
      titulo: 'Venda da lojinha',
      data: dataPedido,
      observacao: pedido.observacao,
      itens: pedido.itens.map((item) {
        return '${item.quantidade}x ${item.nomeProduto} - R\$ ${item.subtotal.toStringAsFixed(2)}';
      }).toList(),
      total: pedido.totalPedido,
    );
  }
}

class _BebidaCard extends StatelessWidget {
  final BebidaConta bebida;

  const _BebidaCard({required this.bebida});

  @override
  Widget build(BuildContext context) {
    // Card de bebida no mesmo padrao visual dos itens da lojinha.
    final dataPedido = _formatarDataConta(bebida.createdAt);

    return ConsumoCard(
      titulo: 'Bebida',
      data: dataPedido,
      observacao: bebida.observacao,
      itens: [
        '${bebida.quantidade}x ${bebida.nomeProduto} - R\$ ${bebida.subtotal.toStringAsFixed(2)}',
      ],
      total: bebida.subtotal,
    );
  }
}

class _LavanderiaCard extends StatelessWidget {
  final OrdemLavanderia ordem;

  const _LavanderiaCard({required this.ordem});

  @override
  Widget build(BuildContext context) {
    final dataPedido = _formatarDataConta(ordem.dtRecebimento);

    return ConsumoCard(
      titulo: 'Lavanderia - ${ordem.statusOrdem}',
      data: dataPedido,
      observacao: ordem.observacao,
      itens: ordem.itens.map((item) {
        return '${item.quantidade}x ${item.nomeServico} - R\$ ${item.subtotal.toStringAsFixed(2)}';
      }).toList(),
      total: ordem.totalOrdem,
    );
  }
}

class _MensagemCard extends StatelessWidget {
  final String mensagem;

  const _MensagemCard({required this.mensagem});

  @override
  Widget build(BuildContext context) {
    // Mensagem neutra usada para estado vazio, erro ou ausencia de registros.
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFFF4F6F3),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Text(mensagem),
    );
  }
}
