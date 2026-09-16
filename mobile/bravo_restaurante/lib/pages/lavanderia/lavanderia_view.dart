import 'package:bravo_restaurante/models/lavanderia.dart';
import 'package:bravo_restaurante/models/reserva.dart';
import 'package:bravo_restaurante/mvvm/lavanderia_viewmodel.dart';
import 'package:bravo_restaurante/mvvm/reserva_viewmodel.dart';
import 'package:bravo_restaurante/widgets/alerta_informacoes_pagina.dart';
import 'package:bravo_restaurante/widgets/botao_acao_principal.dart';
import 'package:bravo_restaurante/widgets/botao_acao_secundaria.dart';
import 'package:bravo_restaurante/widgets/consumo_card.dart';
import 'package:bravo_restaurante/widgets/cores_app.dart';
import 'package:bravo_restaurante/widgets/reserva_dropdown.dart';
import 'package:bravo_restaurante/widgets/rotulo_formulario.dart';
import 'package:bravo_restaurante/widgets/seletor_quantidade.dart';
import 'package:bravo_restaurante/widgets/total_card.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

class LavanderiaView extends StatefulWidget {
  const LavanderiaView({super.key});

  @override
  State<LavanderiaView> createState() => _LavanderiaViewState();
}

class _LavanderiaViewState extends State<LavanderiaView> {
  final _formKey = GlobalKey<FormState>();
  final _observacaoItemController = TextEditingController();
  final _observacaoOrdemController = TextEditingController();
  final List<ItemLavanderiaTemporario> itensOrdem = [];

  Reserva? reservaSelecionada;
  CategoriaLavanderia? categoriaSelecionada;
  ServicoLavanderia? servicoSelecionado;
  int quantidade = 1;

  double get totalOrdem {
    double total = 0;
    for (final item in itensOrdem) {
      total += item.subtotal;
    }
    return total;
  }

  @override
  void initState() {
    super.initState();

    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;

      context.read<ReservaViewModel>().carregarReservasAbertas();
      context.read<LavanderiaViewModel>().carregarCatalogo();
    });
  }

  @override
  void dispose() {
    _observacaoItemController.dispose();
    _observacaoOrdemController.dispose();
    super.dispose();
  }

  void _aumentarQuantidade() {
    setState(() {
      quantidade++;
    });
  }

  void _diminuirQuantidade() {
    if (quantidade <= 1) return;
    setState(() {
      quantidade--;
    });
  }

  void _adicionarItem() {
    if (!_formKey.currentState!.validate()) return;

    if (reservaSelecionada == null) {
      _mostrarMensagem('Selecione uma reserva/quarto.');
      return;
    }

    if (servicoSelecionado == null) {
      _mostrarMensagem('Selecione uma peca.');
      return;
    }

    final item = ItemLavanderiaTemporario(
      servico: servicoSelecionado!,
      quantidade: quantidade,
      observacao: _observacaoItemController.text.trim(),
    );

    setState(() {
      itensOrdem.add(item);
      servicoSelecionado = null;
      quantidade = 1;
      _observacaoItemController.clear();
    });

    _mostrarMensagem('Peca adicionada.');
  }

  void _cancelarOrdem() {
    setState(() {
      reservaSelecionada = null;
      categoriaSelecionada = null;
      servicoSelecionado = null;
      quantidade = 1;
      itensOrdem.clear();
      _observacaoItemController.clear();
      _observacaoOrdemController.clear();
    });

    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) _formKey.currentState?.reset();
    });
    _mostrarMensagem('Ordem de lavanderia cancelada.');
  }

  Future<void> _confirmarOrdem() async {
    if (reservaSelecionada == null) {
      _mostrarMensagem('Selecione uma reserva/quarto.');
      return;
    }

    if (itensOrdem.isEmpty) {
      _mostrarMensagem('Adicione pelo menos uma peca.');
      return;
    }

    final confirmar = await _mostrarConfirmacaoOrdem();
    if (!mounted || !confirmar) return;

    final sucesso = await context.read<LavanderiaViewModel>().criarOrdem(
      reserva: reservaSelecionada!,
      itens: List<ItemLavanderiaTemporario>.from(itensOrdem),
      observacao: _observacaoOrdemController.text,
    );

    if (!mounted) return;

    if (!sucesso) {
      final erro = context.read<LavanderiaViewModel>().mensagemErro;
      _mostrarMensagem(erro ?? 'Erro ao confirmar lavanderia.');
      return;
    }

    setState(() {
      categoriaSelecionada = null;
      servicoSelecionado = null;
      quantidade = 1;
      itensOrdem.clear();
      _observacaoItemController.clear();
      _observacaoOrdemController.clear();
    });

    _mostrarMensagem('Lavanderia lancada na conta do cliente.');
  }

  Future<bool> _mostrarConfirmacaoOrdem() async {
    final reserva = reservaSelecionada;

    if (reserva == null) return false;

    final confirmar = await showDialog<bool>(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: const Text('Confirmar lavanderia'),
          content: SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text('Reserva: ${reserva.descricaoDropdown}'),
                const SizedBox(height: 10),
                const Text(
                  'Pecas:',
                  style: TextStyle(fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 6),
                ...itensOrdem.map((item) {
                  return Padding(
                    padding: const EdgeInsets.only(bottom: 4),
                    child: Text(
                      '${item.quantidade}x ${item.servico.nomeServico} - R\$ ${item.subtotal.toStringAsFixed(2)}',
                    ),
                  );
                }),
                const Divider(height: 24),
                Text(
                  'Total: R\$ ${totalOrdem.toStringAsFixed(2)}',
                  style: const TextStyle(fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 12),
                const Text(
                  'Deseja lancar esta lavanderia na conta do cliente?',
                ),
              ],
            ),
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

    return confirmar == true;
  }

  void _mostrarMensagem(String mensagem) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(mensagem), behavior: SnackBarBehavior.floating),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Consumer2<ReservaViewModel, LavanderiaViewModel>(
      builder: (context, reservaVM, lavanderiaVM, child) {
        final carregando = reservaVM.isLoading || lavanderiaVM.isLoading;
        final servicosDaCategoria = lavanderiaVM.servicos
            .where(
              (servico) =>
                  categoriaSelecionada == null ||
                  servico.idCategoria == categoriaSelecionada!.idCategoria,
            )
            .toList();

        return Scaffold(
          backgroundColor: Colors.white,
          appBar: AppBar(
            title: const Text(
              'Lavanderia',
              style: TextStyle(fontWeight: FontWeight.bold),
            ),
            backgroundColor: CoresApp.verdeEscuro,
            foregroundColor: Colors.white,
          ),
          body: carregando
              ? const Center(child: CircularProgressIndicator())
              : SingleChildScrollView(
                  padding: const EdgeInsets.all(20),
                  child: Form(
                    key: _formKey,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const AlertaInformacoesPagina(
                          message:
                              'Lance apenas roupas pessoais dos turistas. Cama e banho nao entram na lavanderia.',
                        ),
                        const SizedBox(height: 18),
                        const RotuloFormulario('Reserva / Quarto'),
                        const SizedBox(height: 6),
                        _buildDropdownReserva(reservaVM),
                        const SizedBox(height: 18),
                        const RotuloFormulario('Categoria'),
                        const SizedBox(height: 6),
                        _buildDropdownCategoria(lavanderiaVM.categorias),
                        const SizedBox(height: 18),
                        const RotuloFormulario('Peca'),
                        const SizedBox(height: 6),
                        _buildDropdownServico(servicosDaCategoria),
                        const SizedBox(height: 18),
                        const RotuloFormulario('Quantidade'),
                        const SizedBox(height: 6),
                        SeletorQuantidade(
                          quantidade: quantidade,
                          habilitado: servicoSelecionado != null,
                          aoAumentar: _aumentarQuantidade,
                          aoDiminuir: _diminuirQuantidade,
                        ),
                        const SizedBox(height: 18),
                        const RotuloFormulario('Observacao da peca'),
                        const SizedBox(height: 6),
                        _buildObservacaoItemField(),
                        const SizedBox(height: 18),
                        _buildBotaoAdicionar(),
                        if (itensOrdem.isNotEmpty) ...[
                          const SizedBox(height: 24),
                          _buildItensOrdem(),
                          const SizedBox(height: 16),
                          const RotuloFormulario('Observacao da ordem'),
                          const SizedBox(height: 6),
                          _buildObservacaoOrdemField(),
                          const SizedBox(height: 16),
                          TotalCard(
                            titulo: 'Total da lavanderia',
                            valor: totalOrdem,
                          ),
                          const SizedBox(height: 14),
                          _buildBotaoConfirmar(lavanderiaVM),
                          const SizedBox(height: 10),
                          _buildBotaoCancelar(lavanderiaVM),
                        ],
                      ],
                    ),
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
      onChanged: (value) {
        setState(() {
          reservaSelecionada = value;
        });
      },
      validator: (value) {
        if (value == null) return 'Selecione uma reserva';
        return null;
      },
    );
  }

  Widget _buildDropdownCategoria(List<CategoriaLavanderia> categorias) {
    if (categorias.isEmpty) {
      return const Text(
        'Nenhuma categoria de lavanderia ativa.',
        style: TextStyle(color: Colors.red),
      );
    }

    return DropdownButtonFormField<CategoriaLavanderia>(
      initialValue: categoriaSelecionada,
      decoration: const InputDecoration(
        border: OutlineInputBorder(),
        contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 14),
      ),
      hint: const Text('Selecione a categoria'),
      items: categorias.map((categoria) {
        return DropdownMenuItem<CategoriaLavanderia>(
          value: categoria,
          child: Text(categoria.nomeCategoria),
        );
      }).toList(),
      onChanged: (value) {
        setState(() {
          categoriaSelecionada = value;
          servicoSelecionado = null;
          quantidade = 1;
        });
      },
      validator: (value) {
        if (value == null) return 'Selecione uma categoria';
        return null;
      },
    );
  }

  Widget _buildDropdownServico(List<ServicoLavanderia> servicos) {
    final servicoLiberado =
        reservaSelecionada != null &&
        categoriaSelecionada != null &&
        servicos.isNotEmpty;

    if (categoriaSelecionada != null && servicos.isEmpty) {
      return const Text(
        'Nenhuma peca ativa nesta categoria.',
        style: TextStyle(color: Colors.red),
      );
    }

    return DropdownButtonFormField<ServicoLavanderia>(
      initialValue: servicoSelecionado,
      decoration: InputDecoration(
        border: const OutlineInputBorder(),
        contentPadding: const EdgeInsets.symmetric(
          horizontal: 12,
          vertical: 14,
        ),
        filled: !servicoLiberado,
        fillColor: !servicoLiberado ? Colors.grey.shade100 : Colors.white,
      ),
      hint: Text(
        servicoLiberado
            ? 'Selecione a peca'
            : 'Selecione reserva e categoria primeiro',
      ),
      items: servicoLiberado
          ? servicos.map((servico) {
              return DropdownMenuItem<ServicoLavanderia>(
                value: servico,
                child: Text(
                  '${servico.nomeServico} - R\$ ${servico.precoUnitario.toStringAsFixed(2)}',
                ),
              );
            }).toList()
          : [],
      onChanged: servicoLiberado
          ? (value) {
              setState(() {
                servicoSelecionado = value;
                quantidade = 1;
              });
            }
          : null,
      validator: (value) {
        if (reservaSelecionada == null) {
          return 'Selecione primeiro a reserva/quarto';
        }
        if (categoriaSelecionada == null) {
          return 'Selecione uma categoria';
        }
        if (value == null) return 'Selecione uma peca';
        return null;
      },
    );
  }

  Widget _buildObservacaoItemField() {
    return TextFormField(
      controller: _observacaoItemController,
      minLines: 2,
      maxLines: 3,
      decoration: const InputDecoration(
        border: OutlineInputBorder(),
        hintText: 'Ex: lavar separado, mancha, cor delicada...',
      ),
    );
  }

  Widget _buildObservacaoOrdemField() {
    return TextFormField(
      controller: _observacaoOrdemController,
      minLines: 3,
      maxLines: 4,
      decoration: const InputDecoration(
        border: OutlineInputBorder(),
        hintText: 'Ex: entregar no fim da tarde...',
      ),
    );
  }

  Widget _buildBotaoAdicionar() {
    final habilitado = reservaSelecionada != null && servicoSelecionado != null;

    return BotaoAcaoPrincipal(
      label: 'Adicionar Peca',
      icon: Icons.add,
      onPressed: habilitado ? _adicionarItem : null,
      backgroundColor: CoresApp.verdeMedio,
    );
  }

  Widget _buildItensOrdem() {
    return ConsumoCard(
      titulo: 'Pecas da lavanderia',
      data: '${itensOrdem.length} item(ns)',
      itens: itensOrdem.asMap().entries.map((entry) {
        final index = entry.key;
        final item = entry.value;
        return '${index + 1}. ${item.quantidade}x ${item.servico.nomeServico} - R\$ ${item.subtotal.toStringAsFixed(2)}';
      }).toList(),
      total: totalOrdem,
    );
  }

  Widget _buildBotaoConfirmar(LavanderiaViewModel lavanderiaVM) {
    final habilitado = itensOrdem.isNotEmpty && !lavanderiaVM.isSaving;

    return BotaoAcaoPrincipal(
      label: lavanderiaVM.isSaving ? 'Salvando...' : 'Confirmar Lavanderia',
      icon: Icons.check,
      onPressed: habilitado ? _confirmarOrdem : null,
    );
  }

  Widget _buildBotaoCancelar(LavanderiaViewModel lavanderiaVM) {
    final habilitado = itensOrdem.isNotEmpty && !lavanderiaVM.isSaving;

    return BotaoAcaoSecundaria(
      label: 'Cancelar Ordem',
      icon: Icons.close,
      onPressed: habilitado ? _cancelarOrdem : null,
      foregroundColor: Colors.red.shade700,
      borderColor: Colors.red.shade300,
    );
  }
}
