import 'package:bravo_restaurante/models/reserva.dart';
import 'package:bravo_restaurante/models/resumo_fechamento_conta.dart';
import 'package:bravo_restaurante/mvvm/conta_consumo_viewmodel.dart';
import 'package:bravo_restaurante/mvvm/reserva_viewmodel.dart';
import 'package:bravo_restaurante/widgets/alerta_informacoes_pagina.dart';
import 'package:bravo_restaurante/widgets/botao_acao_principal.dart';
import 'package:bravo_restaurante/widgets/botao_acao_secundaria.dart';
import 'package:bravo_restaurante/widgets/consumo_card.dart';
import 'package:bravo_restaurante/widgets/cores_app.dart';
import 'package:bravo_restaurante/widgets/reserva_dropdown.dart';
import 'package:bravo_restaurante/widgets/rotulo_formulario.dart';
import 'package:bravo_restaurante/widgets/total_card.dart';
import 'package:flutter/material.dart';
import 'package:pdf/widgets.dart' as pw;
import 'package:printing/printing.dart';
import 'package:provider/provider.dart';

class FecharContaView extends StatefulWidget {
  const FecharContaView({super.key});

  @override
  State<FecharContaView> createState() => _FecharContaViewState();
}

class _FecharContaViewState extends State<FecharContaView> {
  // Reserva escolhida no dropdown; a partir dela a conta sera carregada.
  Reserva? reservaSelecionada;

  @override
  void initState() {
    super.initState();

    // Carrega as reservas abertas depois que a tela foi criada.
    Future.microtask(() {
      // ignore: use_build_context_synchronously
      context.read<ReservaViewModel>().carregarReservasAbertas();
    });
  }

  Future<void> _carregarResumoConta(Reserva reserva) async {
    final contaVM = context.read<ContaConsumoViewModel>();
    await contaVM.carregarResumoFechamento(reserva);
  }

  Future<void> _fecharConta() async {
    if (reservaSelecionada == null) {
      _mostrarMensagem('Selecione uma reserva.');
      return;
    }

    final contaVM = context.read<ContaConsumoViewModel>();
    final totalConta = contaVM.resumoFechamento?.totalConta ?? 0.0;

    final confirmar = await showDialog<bool>(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: const Text('Fechar conta'),
          content: Text(
            'Deseja realmente fechar a conta no valor de R\$ ${totalConta.toStringAsFixed(2)}?',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('Cancelar'),
            ),
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: CoresApp.verdeEscuro,
                foregroundColor: Colors.white,
              ),
              onPressed: () => Navigator.pop(context, true),
              child: const Text('Confirmar'),
            ),
          ],
        );
      },
    );

    if (confirmar != true) return;

    final sucesso = await contaVM.fecharContaDaReserva(reservaSelecionada!);

    if (!mounted) return;

    if (!sucesso) {
      _mostrarMensagem(
        contaVM.mensagemErroFechamento ?? 'Erro ao fechar conta.',
      );
      return;
    }

    _mostrarMensagem('Conta fechada com sucesso.');

    setState(() {
      reservaSelecionada = null;
    });

    context.read<ReservaViewModel>().carregarReservasAbertas();
  }

  void _mostrarMensagem(String mensagem) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(mensagem), behavior: SnackBarBehavior.floating),
    );
  }

  String _formatarDataPedido(DateTime? data) {
    if (data == null) return 'Data nao informada';

    final dataLocal = data.toLocal();
    String doisDigitos(int numero) => numero.toString().padLeft(2, '0');

    final dia = doisDigitos(dataLocal.day);
    final mes = doisDigitos(dataLocal.month);
    final hora = doisDigitos(dataLocal.hour);
    final minuto = doisDigitos(dataLocal.minute);

    return '$dia/$mes/${dataLocal.year} $hora:$minuto';
  }

  Future<void> _gerarRelatorioConta() async {
    if (reservaSelecionada == null) {
      _mostrarMensagem('Selecione uma reserva para gerar o relatorio.');
      return;
    }

    final resumo = context.read<ContaConsumoViewModel>().resumoFechamento;

    if (resumo == null) {
      _mostrarMensagem(
        'Carregue o resumo da conta antes de gerar o relatorio.',
      );
      return;
    }

    final pdf = pw.Document();
    final reserva = reservaSelecionada!;

    pdf.addPage(
      pw.MultiPage(
        build: (context) => [
          pw.Text(
            'BRAVO Consumo',
            style: pw.TextStyle(fontSize: 20, fontWeight: pw.FontWeight.bold),
          ),
          pw.SizedBox(height: 8),
          pw.Text('Relatorio da Conta do Hospede'),
          pw.Divider(),
          pw.Text('Hospede: ${reserva.nomeHospede}'),
          pw.Text('Quarto: ${reserva.numeroQuarto}'),
          pw.Text('Status da Conta: ${reserva.statusConta}'),
          pw.SizedBox(height: 16),
          pw.Text(
            'Lojinha',
            style: pw.TextStyle(fontWeight: pw.FontWeight.bold),
          ),
          if (resumo.pedidos.isEmpty)
            pw.Text('Nenhum produto da lojinha registrado.')
          else
            ...resumo.pedidos.map((pedido) {
              final dataPedido = _formatarDataPedido(pedido.createdAt);

              return pw.Column(
                crossAxisAlignment: pw.CrossAxisAlignment.start,
                children: [
                  pw.SizedBox(height: 8),
                  pw.Text(
                    'Venda da lojinha',
                    style: pw.TextStyle(fontWeight: pw.FontWeight.bold),
                  ),
                  pw.Text('Data: $dataPedido'),
                  ...pedido.itens.map((item) {
                    return pw.Text(
                      '${item.quantidade}x ${item.nomeProduto} - R\$ ${item.subtotal.toStringAsFixed(2)}',
                    );
                  }),
                  pw.Text(
                    'Total do lancamento: R\$ ${pedido.totalPedido.toStringAsFixed(2)}',
                  ),
                ],
              );
            }),
          pw.SizedBox(height: 16),
          pw.Text(
            'Bebidas',
            style: pw.TextStyle(fontWeight: pw.FontWeight.bold),
          ),
          if (resumo.bebidas.isEmpty)
            pw.Text('Nenhuma bebida lancada.')
          else
            ...resumo.bebidas.map((bebida) {
              final dataPedido = _formatarDataPedido(bebida.createdAt);

              return pw.Column(
                crossAxisAlignment: pw.CrossAxisAlignment.start,
                children: [
                  pw.SizedBox(height: 8),
                  pw.Text(
                    'Bebida',
                    style: pw.TextStyle(fontWeight: pw.FontWeight.bold),
                  ),
                  pw.Text('Data: $dataPedido'),
                  pw.Text(
                    '${bebida.quantidade}x ${bebida.nomeProduto} - R\$ ${bebida.subtotal.toStringAsFixed(2)}',
                  ),
                  pw.Text(
                    'Total do lancamento: R\$ ${bebida.subtotal.toStringAsFixed(2)}',
                  ),
                ],
              );
            }),
          pw.Divider(),
          pw.Align(
            alignment: pw.Alignment.centerRight,
            child: pw.Text(
              'TOTAL: R\$ ${resumo.totalConta.toStringAsFixed(2)}',
              style: pw.TextStyle(fontSize: 18, fontWeight: pw.FontWeight.bold),
            ),
          ),
        ],
      ),
    );

    await Printing.layoutPdf(onLayout: (format) async => pdf.save());
  }

  @override
  Widget build(BuildContext context) {
    return Consumer2<ReservaViewModel, ContaConsumoViewModel>(
      builder: (context, reservaVM, contaVM, child) {
        return Scaffold(
          backgroundColor: Colors.white,
          appBar: AppBar(
            title: const Text(
              'Fechar Conta',
              style: TextStyle(fontWeight: FontWeight.bold),
            ),
            backgroundColor: CoresApp.verdeEscuro,
            foregroundColor: Colors.white,
          ),
          body: SingleChildScrollView(
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const AlertaInformacoesPagina(
                  message:
                      'Revise o consumo antes de fechar a conta da reserva.',
                ),
                const SizedBox(height: 18),
                const RotuloFormulario('Selecione a Reserva'),
                const SizedBox(height: 6),
                _buildDropdownReserva(reservaVM),
                const SizedBox(height: 18),
                if (reservaSelecionada != null) _buildCardReserva(),
                if (contaVM.carregandoResumoFechamento)
                  const Padding(
                    padding: EdgeInsets.all(24),
                    child: Center(child: CircularProgressIndicator()),
                  ),
                if (contaVM.mensagemErroFechamento != null)
                  Text(
                    contaVM.mensagemErroFechamento!,
                    style: const TextStyle(color: Colors.red),
                  ),
                if (!contaVM.carregandoResumoFechamento &&
                    reservaSelecionada != null &&
                    contaVM.resumoFechamento != null) ...[
                  const SizedBox(height: 18),
                  _buildResumoConta(contaVM.resumoFechamento!),
                  const SizedBox(height: 18),
                  _buildBotaoFecharConta(),
                  const SizedBox(height: 10),
                  _buildBotaoComprovante(),
                  const SizedBox(height: 10),
                  _buildAvisoFinal(),
                ],
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildDropdownReserva(ReservaViewModel reservaVM) {
    return ReservaDropdown(
      reservaVM: reservaVM,
      reservaSelecionada: reservaSelecionada,
      mostrarLoading: true,
      onChanged: (value) {
        setState(() {
          reservaSelecionada = value;
        });

        if (value != null) {
          _carregarResumoConta(value);
        } else {
          context.read<ContaConsumoViewModel>().limparResumoFechamento();
        }
      },
    );
  }

  Widget _buildCardReserva() {
    final reserva = reservaSelecionada!;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFFF4F6F3),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: Colors.grey.shade300),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Reserva', style: TextStyle(fontSize: 12)),
          Text(
            reserva.nomeHospede,
            style: const TextStyle(
              fontWeight: FontWeight.bold,
              fontSize: 16,
              color: CoresApp.verdeEscuro,
            ),
          ),
          Text('Quarto ${reserva.numeroQuarto}'),
          const SizedBox(height: 6),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
              color: Colors.green.shade100,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Text(
              reserva.statusConta,
              style: const TextStyle(
                fontSize: 12,
                color: CoresApp.verdeEscuro,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildResumoConta(ResumoFechamentoConta resumo) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Resumo da Conta do Cliente',
          style: TextStyle(
            fontWeight: FontWeight.bold,
            color: CoresApp.cinzaEscuro,
            fontSize: 16,
          ),
        ),
        const SizedBox(height: 10),
        const Text('Lojinha', style: TextStyle(fontWeight: FontWeight.w600)),
        const SizedBox(height: 6),
        if (resumo.pedidos.isEmpty)
          const Text('Nenhum produto da lojinha registrado.')
        else
          ...resumo.pedidos.map((pedido) => _buildPedidoCard(pedido)),
        const SizedBox(height: 14),
        const Text('Bebidas', style: TextStyle(fontWeight: FontWeight.w600)),
        const SizedBox(height: 6),
        if (resumo.bebidas.isEmpty)
          const Text('Nenhuma bebida lancada.')
        else
          ...resumo.bebidas.map((bebida) => _buildBebidaCard(bebida)),
        const SizedBox(height: 14),
        TotalCard(
          titulo: 'Total Acumulado na Conta do Cliente',
          valor: resumo.totalConta,
          backgroundColor: CoresApp.verdeEscuro,
          valorFontSize: 26,
        ),
      ],
    );
  }

  Widget _buildPedidoCard(PedidoResumoConta pedido) {
    final dataPedido = _formatarDataPedido(pedido.createdAt);

    return ConsumoCard(
      titulo: 'Venda da lojinha',
      data: dataPedido,
      itens: pedido.itens.map((item) {
        return '${item.quantidade}x ${item.nomeProduto} - R\$ ${item.subtotal.toStringAsFixed(2)}';
      }).toList(),
      total: pedido.totalPedido,
    );
  }

  Widget _buildBebidaCard(BebidaResumoConta bebida) {
    final dataPedido = _formatarDataPedido(bebida.createdAt);

    return ConsumoCard(
      titulo: 'Bebida',
      data: dataPedido,
      itens: [
        '${bebida.quantidade}x ${bebida.nomeProduto} - R\$ ${bebida.subtotal.toStringAsFixed(2)}',
      ],
      total: bebida.subtotal,
    );
  }

  Widget _buildBotaoFecharConta() {
    return BotaoAcaoPrincipal(
      label: 'Fechar Conta',
      icon: Icons.attach_money,
      onPressed: _fecharConta,
    );
  }

  Widget _buildBotaoComprovante() {
    return BotaoAcaoSecundaria(
      label: 'Gerar Comprovante',
      icon: Icons.description_outlined,
      onPressed: _gerarRelatorioConta,
    );
  }

  Widget _buildAvisoFinal() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFFEAF3FF),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.blue.shade100),
      ),
      child: const Text(
        'Ao fechar a conta, nenhum novo consumo podera ser adicionado a Conta do Cliente.',
        style: TextStyle(fontSize: 13),
      ),
    );
  }
}
