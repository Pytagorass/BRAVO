import 'package:bravo_restaurante/models/item_pedido_temporario.dart';
import 'package:bravo_restaurante/models/produto.dart';
import 'package:bravo_restaurante/models/reserva.dart';
import 'package:bravo_restaurante/mvvm/pedido_viewmodel.dart';
import 'package:bravo_restaurante/mvvm/produto_viewmodel.dart';
import 'package:bravo_restaurante/mvvm/reserva_viewmodel.dart';
import 'package:bravo_restaurante/mvvm/usuario_viewmodel.dart';
import 'package:bravo_restaurante/widgets/alerta_informacoes_pagina.dart';
import 'package:bravo_restaurante/widgets/botao_acao_principal.dart';
import 'package:bravo_restaurante/widgets/botao_acao_secundaria.dart';
import 'package:bravo_restaurante/widgets/cores_app.dart';
import 'package:bravo_restaurante/widgets/reserva_dropdown.dart';
import 'package:bravo_restaurante/widgets/rotulo_formulario.dart';
import 'package:bravo_restaurante/widgets/seletor_quantidade.dart';
import 'package:bravo_restaurante/widgets/total_card.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

class RegistrarPedidoView extends StatefulWidget {
  final String origem;
  final String titulo;

  const RegistrarPedidoView({
    super.key,
    this.origem = 'Restaurante',
    this.titulo = 'Registrar Pedido',
  });

  @override
  State<RegistrarPedidoView> createState() => _RegistrarPedidoViewState();
}

class _RegistrarPedidoViewState extends State<RegistrarPedidoView> {
  final _formKey = GlobalKey<FormState>();
  final _observacaoController = TextEditingController();
  final List<ItemPedidoTemporario> itensPedido = [];

  Reserva? reservaSelecionada;
  Produto? produtoSelecionado;
  int quantidade = 1;
  bool salvandoPedido = false;

  double get totalPedido {
    double total = 0;
    for (final item in itensPedido) {
      total += item.subtotal;
    }
    return total;
  }

  bool get _ehLojinha => widget.origem == 'Lojinha';

  @override
  void initState() {
    super.initState();

    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;

      context.read<ProdutoViewModel>().carregarProdutos(origem: widget.origem);
      context.read<ReservaViewModel>().carregarReservasAbertas();
    });
  }

  @override
  void dispose() {
    _observacaoController.dispose();
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

    if (produtoSelecionado == null) {
      _mostrarMensagem('Selecione um produto.');
      return;
    }

    final item = ItemPedidoTemporario(
      produto: produtoSelecionado!,
      quantidade: quantidade,
      observacao: _observacaoController.text.trim(),
    );

    setState(() {
      itensPedido.add(item);
      produtoSelecionado = null;
      quantidade = 1;
      _observacaoController.clear();
    });

    _mostrarMensagem('Item adicionado.');
  }

  void _cancelarPedido() {
    if (salvandoPedido) return;

    setState(() {
      itensPedido.clear();
      reservaSelecionada = null;
      produtoSelecionado = null;
      quantidade = 1;
      _observacaoController.clear();
    });

    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) _formKey.currentState?.reset();
    });
    _mostrarMensagem('Lancamento cancelado.');
  }

  void _removerItemPedido(int index) {
    if (salvandoPedido) return;

    setState(() {
      itensPedido.removeAt(index);
    });

    _mostrarMensagem('Item removido.');
  }

  Future<void> _editarQuantidadeItem(int index) async {
    if (salvandoPedido) return;

    final item = itensPedido[index];
    var novaQuantidade = item.quantidade;

    final quantidadeEditada = await showDialog<int>(
      context: context,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setDialogState) {
            return AlertDialog(
              title: const Text('Editar quantidade'),
              content: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  IconButton(
                    onPressed: novaQuantidade > 1
                        ? () {
                            setDialogState(() {
                              novaQuantidade--;
                            });
                          }
                        : null,
                    icon: const Icon(Icons.remove),
                  ),
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 18),
                    child: Text(
                      novaQuantidade.toString(),
                      style: const TextStyle(
                        fontSize: 20,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                  IconButton(
                    onPressed: () {
                      setDialogState(() {
                        novaQuantidade++;
                      });
                    },
                    icon: const Icon(Icons.add),
                  ),
                ],
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(context),
                  child: const Text('Cancelar'),
                ),
                ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: CoresApp.verdeEscuro,
                    foregroundColor: Colors.white,
                  ),
                  onPressed: () => Navigator.pop(context, novaQuantidade),
                  child: const Text('Salvar'),
                ),
              ],
            );
          },
        );
      },
    );

    if (quantidadeEditada == null || !mounted) return;

    setState(() {
      itensPedido[index] = ItemPedidoTemporario(
        produto: item.produto,
        quantidade: quantidadeEditada,
        observacao: item.observacao,
      );
    });

    _mostrarMensagem('Quantidade atualizada.');
  }

  Future<void> _confirmarPedido() async {
    if (reservaSelecionada == null) {
      _mostrarMensagem('Selecione uma reserva/quarto.');
      return;
    }

    if (itensPedido.isEmpty) {
      _mostrarMensagem('Adicione pelo menos um item.');
      return;
    }

    setState(() {
      salvandoPedido = true;
    });

    final usuarioLogado = context.read<UsuarioViewModel>().usuarioLogado;
    if (usuarioLogado == null) {
      setState(() {
        salvandoPedido = false;
      });
      _mostrarMensagem('Usuario logado nao encontrado.');
      return;
    }

    final pedidoVM = context.read<PedidoViewModel>();
    final sucesso = await pedidoVM.gravarContaConsumo(
      reserva: reservaSelecionada!,
      itens: List<ItemPedidoTemporario>.from(itensPedido),
      total: totalPedido,
      idUsuario: usuarioLogado.idUsuario,
      origem: widget.origem,
      observacao: _observacaoPedido(),
    );

    if (!mounted) return;

    setState(() {
      salvandoPedido = false;
    });

    if (!sucesso) {
      _mostrarMensagem(pedidoVM.mensagemErro ?? 'Erro ao confirmar consumo.');
      return;
    }

    setState(() {
      itensPedido.clear();
      reservaSelecionada = null;
      produtoSelecionado = null;
      quantidade = 1;
      _observacaoController.clear();
    });

    _mostrarMensagem('Consumo confirmado e vinculado a conta do cliente.');
  }

  String? _observacaoPedido() {
    final observacoes = itensPedido
        .where((item) => item.observacao.trim().isNotEmpty)
        .map((item) => '${item.produto.nomeProduto}: ${item.observacao.trim()}')
        .join('\n');

    return observacoes.isEmpty ? null : observacoes;
  }

  void _mostrarMensagem(String mensagem) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(mensagem), behavior: SnackBarBehavior.floating),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Consumer2<ProdutoViewModel, ReservaViewModel>(
      builder: (context, produtoVM, reservaVM, child) {
        final carregando = produtoVM.isLoading || reservaVM.isLoading;

        return Scaffold(
          backgroundColor: Colors.white,
          appBar: AppBar(
            title: Text(
              widget.titulo,
              style: const TextStyle(fontWeight: FontWeight.bold),
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
                        AlertaInformacoesPagina(
                          message:
                              'Registre o consumo de ${widget.titulo.toLowerCase()} e vincule a uma reserva aberta.',
                        ),
                        const SizedBox(height: 18),
                        const RotuloFormulario('Reserva / Quarto'),
                        const SizedBox(height: 6),
                        _buildDropdownReserva(reservaVM),
                        const SizedBox(height: 18),
                        const RotuloFormulario('Produto'),
                        const SizedBox(height: 6),
                        _buildDropdownProduto(produtoVM),
                        const SizedBox(height: 18),
                        const RotuloFormulario('Quantidade'),
                        const SizedBox(height: 6),
                        SeletorQuantidade(
                          quantidade: quantidade,
                          habilitado: produtoSelecionado != null,
                          aoAumentar: _aumentarQuantidade,
                          aoDiminuir: _diminuirQuantidade,
                        ),
                        const SizedBox(height: 18),
                        const RotuloFormulario('Observacao'),
                        const SizedBox(height: 6),
                        _buildObservacaoField(),
                        const SizedBox(height: 22),
                        _buildBotaoAdicionar(),
                        if (itensPedido.isNotEmpty) ...[
                          const SizedBox(height: 24),
                          const Text(
                            'Itens',
                            style: TextStyle(
                              fontWeight: FontWeight.bold,
                              fontSize: 16,
                              color: CoresApp.cinzaEscuro,
                            ),
                          ),
                          const SizedBox(height: 10),
                          Card(
                            elevation: 2,
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(10),
                            ),
                            child: ListView.builder(
                              shrinkWrap: true,
                              physics: const NeverScrollableScrollPhysics(),
                              itemCount: itensPedido.length,
                              itemBuilder: (context, index) {
                                final item = itensPedido[index];

                                return ListTile(
                                  title: Text(
                                    '${item.quantidade}x ${item.produto.nomeProduto}',
                                    style: const TextStyle(
                                      fontWeight: FontWeight.w600,
                                    ),
                                  ),
                                  subtitle: Text(
                                    'R\$ ${item.produto.preco.toStringAsFixed(2)} cada',
                                  ),
                                  trailing: Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      Text(
                                        'R\$ ${item.subtotal.toStringAsFixed(2)}',
                                        style: const TextStyle(
                                          fontWeight: FontWeight.bold,
                                          color: CoresApp.verdeEscuro,
                                        ),
                                      ),
                                      IconButton(
                                        tooltip: 'Editar quantidade',
                                        onPressed: salvandoPedido
                                            ? null
                                            : () =>
                                                  _editarQuantidadeItem(index),
                                        icon: const Icon(Icons.edit_outlined),
                                        color: CoresApp.verdeEscuro,
                                      ),
                                      IconButton(
                                        tooltip: 'Remover item',
                                        onPressed: salvandoPedido
                                            ? null
                                            : () => _removerItemPedido(index),
                                        icon: const Icon(Icons.delete_outline),
                                        color: Colors.red,
                                      ),
                                    ],
                                  ),
                                );
                              },
                            ),
                          ),
                          const SizedBox(height: 14),
                          TotalCard(titulo: 'Total', valor: totalPedido),
                          const SizedBox(height: 14),
                          BotaoAcaoPrincipal(
                            label: 'Confirmar e Vincular a Conta',
                            icon: Icons.check,
                            onPressed: salvandoPedido ? null : _confirmarPedido,
                            borderRadius: 10,
                          ),
                          const SizedBox(height: 10),
                          _buildBotaoCancelar(),
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
          produtoSelecionado = null;
          quantidade = 1;
        });
      },
      validator: (value) {
        if (value == null) {
          return 'Selecione uma reserva';
        }

        return null;
      },
    );
  }

  Widget _buildDropdownProduto(ProdutoViewModel produtoVM) {
    final produtoLiberado = reservaSelecionada != null;

    if (produtoVM.mensagemErro != null) {
      return Text(
        produtoVM.mensagemErro!,
        style: const TextStyle(color: Colors.red),
      );
    }

    if (produtoVM.produtos.isEmpty) {
      return Text(
        'Nenhum produto ativo encontrado para ${widget.titulo}.',
        style: const TextStyle(color: Colors.red),
      );
    }

    return DropdownButtonFormField<Produto>(
      initialValue: produtoSelecionado,
      decoration: InputDecoration(
        border: const OutlineInputBorder(),
        contentPadding: const EdgeInsets.symmetric(
          horizontal: 12,
          vertical: 14,
        ),
        filled: !produtoLiberado,
        fillColor: !produtoLiberado ? Colors.grey.shade100 : Colors.white,
      ),
      hint: Text(
        produtoLiberado
            ? 'Selecione o produto'
            : 'Selecione primeiro a reserva/quarto',
      ),
      items: produtoLiberado
          ? produtoVM.produtos.map((produto) {
              return DropdownMenuItem<Produto>(
                value: produto,
                child: Text(
                  '${produto.nomeProduto} - R\$ ${produto.preco.toStringAsFixed(2)}',
                ),
              );
            }).toList()
          : [],
      onChanged: produtoLiberado
          ? (value) {
              setState(() {
                produtoSelecionado = value;
                quantidade = 1;
              });
            }
          : null,
      validator: (value) {
        if (reservaSelecionada == null) {
          return 'Selecione primeiro a reserva/quarto';
        }

        if (value == null) {
          return 'Selecione um produto';
        }

        return null;
      },
    );
  }

  Widget _buildObservacaoField() {
    return TextFormField(
      controller: _observacaoController,
      minLines: 4,
      maxLines: 5,
      decoration: InputDecoration(
        border: const OutlineInputBorder(),
        hintText: _ehLojinha
            ? 'Ex: Cor, tamanho, embalagem...'
            : 'Ex: Sem cebola, ponto da carne...',
      ),
    );
  }

  Widget _buildBotaoAdicionar() {
    final habilitado = reservaSelecionada != null && produtoSelecionado != null;

    return BotaoAcaoPrincipal(
      label: 'Adicionar Item',
      icon: Icons.add,
      onPressed: habilitado ? _adicionarItem : null,
      backgroundColor: CoresApp.verdeMedio,
    );
  }

  Widget _buildBotaoCancelar() {
    final habilitado = itensPedido.isNotEmpty && !salvandoPedido;

    return BotaoAcaoSecundaria(
      label: 'Cancelar Lancamento',
      icon: Icons.close,
      onPressed: habilitado ? _cancelarPedido : null,
      foregroundColor: Colors.red.shade700,
      borderColor: Colors.red.shade300,
    );
  }
}
