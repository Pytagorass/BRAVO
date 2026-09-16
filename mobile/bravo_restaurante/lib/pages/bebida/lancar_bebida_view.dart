import 'package:bravo_restaurante/models/produto.dart';
import 'package:bravo_restaurante/models/reserva.dart';
import 'package:bravo_restaurante/mvvm/bebida_viewmodel.dart';
import 'package:bravo_restaurante/mvvm/produto_viewmodel.dart';
import 'package:bravo_restaurante/mvvm/reserva_viewmodel.dart';
import 'package:bravo_restaurante/mvvm/usuario_viewmodel.dart';
import 'package:bravo_restaurante/widgets/cores_app.dart';
import 'package:bravo_restaurante/widgets/rotulo_formulario.dart';
import 'package:bravo_restaurante/widgets/alerta_informacoes_pagina.dart';
import 'package:bravo_restaurante/widgets/botao_acao_principal.dart';
import 'package:bravo_restaurante/widgets/seletor_quantidade.dart';
import 'package:bravo_restaurante/widgets/reserva_dropdown.dart';
import 'package:bravo_restaurante/widgets/botao_acao_secundaria.dart';
import 'package:bravo_restaurante/widgets/total_card.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

class LancarBebidaView extends StatefulWidget {
  const LancarBebidaView({super.key});

  @override
  State<LancarBebidaView> createState() => _LancarBebidaViewState();
}

class _LancarBebidaViewState extends State<LancarBebidaView> {
  // Chave usada para validar todos os campos do formulario.
  final _formKey = GlobalKey<FormState>();

  // Guarda a reserva e a bebida selecionadas pelo usuario.
  Reserva? reservaSelecionada;
  Produto? bebidaSelecionada;

  // Quantidade de bebidas que sera lancada na conta.
  int quantidade = 1;

  // Calcula o valor total com base na bebida escolhida e na quantidade.
  double get total {
    if (bebidaSelecionada == null) return 0;
    return bebidaSelecionada!.preco * quantidade;
  }

  @override
  void initState() {
    super.initState();

    // Carrega reservas abertas e produtos depois do primeiro frame da tela.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;

      context.read<ReservaViewModel>().carregarReservasAbertas();
      context.read<ProdutoViewModel>().carregarProdutos(origem: 'Restaurante');
    });
  }

  void _aumentarQuantidade() {
    // Atualiza a tela somando uma unidade.
    setState(() {
      quantidade++;
    });
  }

  void _diminuirQuantidade() {
    if (quantidade <= 1) return;

    // Atualiza a tela removendo uma unidade sem deixar passar de 1.
    setState(() {
      quantidade--;
    });
  }

  Future<void> _lancarBebida() async {
    // Valida formulario, usuario logado e dados escolhidos antes de salvar.
    if (!_formKey.currentState!.validate()) return;

    if (reservaSelecionada == null) {
      _mostrarMensagem('Selecione uma reserva/quarto.');
      return;
    }

    if (bebidaSelecionada == null) {
      _mostrarMensagem('Selecione uma bebida.');
      return;
    }

    final usuarioLogado = context.read<UsuarioViewModel>().usuarioLogado;

    if (usuarioLogado == null) {
      _mostrarMensagem('Usuário não encontrado. Faça login novamente.');
      return;
    }

    // Envia o lancamento para o ViewModel, que grava no backend.
    final sucesso = await context.read<BebidaViewModel>().lancarBebidaNaConta(
      idReserva: reservaSelecionada!.idReserva,
      idProduto: bebidaSelecionada!.idProduto,
      idUsuario: usuarioLogado.idUsuario,
      quantidade: quantidade,
      valorUnitario: bebidaSelecionada!.preco,
      observacao: 'Lançamento realizado pelo app mobile',
    );

    // Evita atualizar a interface se o usuario saiu da tela durante o envio.
    if (!mounted) return;

    if (sucesso) {
      _mostrarMensagem(
        'Bebida lançada na conta: ${quantidade}x ${bebidaSelecionada!.nomeProduto}',
      );

      // Apos salvar, limpa a bebida e volta a quantidade para o padrao.
      setState(() {
        bebidaSelecionada = null;
        quantidade = 1;
      });
    } else {
      // Mostra a mensagem de erro retornada pelo ViewModel, se existir.
      final erro = context.read<BebidaViewModel>().mensagemErro;
      _mostrarMensagem(erro ?? 'Erro ao lançar bebida.');
    }
  }

  void _cancelarLancamento() {
    setState(() {
      // Cancela o lancamento em montagem antes de gravar no banco.
      reservaSelecionada = null;
      bebidaSelecionada = null;
      quantidade = 1;
    });

    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) _formKey.currentState?.reset();
    });
    _mostrarMensagem('Lançamento de bebida cancelado.');
  }

  void _mostrarMensagem(String mensagem) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(mensagem), behavior: SnackBarBehavior.floating),
    );
  }

  @override
  Widget build(BuildContext context) {
    // Observa reservas e produtos para reconstruir a tela quando os dados mudam.
    return Consumer2<ReservaViewModel, ProdutoViewModel>(
      builder: (context, reservaVM, produtoVM, child) {
        final carregando = reservaVM.isLoading || produtoVM.isLoading;

        // Filtra apenas produtos cadastrados como bebida.
        final bebidas = produtoVM.produtos
            .where(
              (produto) => produto.categoria.toLowerCase().contains('bebida'),
            )
            .toList();

        return Scaffold(
          backgroundColor: Colors.white,
          appBar: AppBar(
            title: const Text(
              'Lançar Bebida',
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
                              'Lançamento rápido de bebida direto na Conta do Cliente.',
                        ),

                        const SizedBox(height: 18),

                        const RotuloFormulario('Reserva / Quarto'),
                        const SizedBox(height: 6),
                        _buildDropdownReserva(reservaVM),

                        const SizedBox(height: 18),

                        const RotuloFormulario('Bebida'),
                        const SizedBox(height: 6),
                        _buildDropdownBebida(bebidas),

                        const SizedBox(height: 18),

                        const RotuloFormulario('Quantidade'),
                        const SizedBox(height: 6),
                        SeletorQuantidade(
                          quantidade: quantidade,
                          habilitado: bebidaSelecionada != null,
                          aoAumentar: _aumentarQuantidade,
                          aoDiminuir: _diminuirQuantidade,
                        ),

                        const SizedBox(height: 18),

                        const RotuloFormulario('Valor Unitário'),
                        const SizedBox(height: 6),
                        _buildValorUnitario(),

                        const SizedBox(height: 18),

                        TotalCard(
                          titulo: 'Total a lançar na Conta do Cliente',
                          valor: total,
                        ),

                        const SizedBox(height: 14),

                        _buildBotaoLancar(),
                        const SizedBox(height: 10),
                        _buildBotaoCancelar(),
                      ],
                    ),
                  ),
                ),
        );
      },
    );
  }

  Widget _buildDropdownReserva(ReservaViewModel reservaVM) {
    // Lista as reservas abertas para escolher em qual conta a bebida entrara.
    return ReservaDropdown(
      reservaVM: reservaVM,
      reservaSelecionada: reservaSelecionada,
      onChanged: (value) {
        setState(() {
          // Trocar de reserva reinicia a bebida e a quantidade escolhidas.
          reservaSelecionada = value;
          bebidaSelecionada = null;
          quantidade = 1;
        });
      },
      validator: (value) {
        // O formulario nao continua sem uma reserva valida.
        if (value == null) {
          return 'Selecione uma reserva';
        }
        return null;
      },
    );
  }

  Widget _buildDropdownBebida(List<Produto> bebidas) {
    // A bebida so pode ser escolhida depois que uma reserva for selecionada.
    final bebidaLiberada = reservaSelecionada != null;

    if (bebidas.isEmpty) {
      return const Text(
        'Nenhuma bebida ativa encontrada.',
        style: TextStyle(color: Colors.red),
      );
    }

    return DropdownButtonFormField<Produto>(
      initialValue: bebidaSelecionada,
      decoration: InputDecoration(
        border: const OutlineInputBorder(),
        contentPadding: const EdgeInsets.symmetric(
          horizontal: 12,
          vertical: 14,
        ),
        filled: !bebidaLiberada,
        fillColor: !bebidaLiberada ? Colors.grey.shade100 : Colors.white,
      ),
      hint: Text(
        bebidaLiberada
            ? 'Selecione a bebida'
            : 'Selecione primeiro a reserva/quarto',
      ),
      items: bebidaLiberada
          ? bebidas.map((bebida) {
              return DropdownMenuItem<Produto>(
                value: bebida,
                child: Text(
                  '${bebida.nomeProduto} - R\$ ${bebida.preco.toStringAsFixed(2)}',
                ),
              );
            }).toList()
          : [],
      onChanged: bebidaLiberada
          ? (value) {
              setState(() {
                // Ao trocar a bebida, a quantidade volta para 1.
                bebidaSelecionada = value;
                quantidade = 1;
              });
            }
          : null,
      validator: (value) {
        // Primeiro exige a reserva, depois exige a bebida.
        if (reservaSelecionada == null) {
          return 'Selecione primeiro a reserva/quarto';
        }

        if (value == null) {
          return 'Selecione uma bebida';
        }

        return null;
      },
    );
  }

  Widget _buildValorUnitario() {
    // Campo somente leitura com o preco da bebida escolhida.
    final valor = bebidaSelecionada?.preco ?? 0.0;

    return TextFormField(
      enabled: false,
      initialValue: 'R\$ ${valor.toStringAsFixed(2)}',
      decoration: InputDecoration(
        border: const OutlineInputBorder(),
        filled: true,
        fillColor: Colors.grey.shade100,
      ),
    );
  }

  Widget _buildBotaoLancar() {
    // Habilita o botao apenas quando reserva e bebida foram selecionadas.
    final habilitado = reservaSelecionada != null && bebidaSelecionada != null;

    return BotaoAcaoPrincipal(
      label: 'Lançar na Conta do Cliente',
      icon: Icons.check,
      onPressed: habilitado ? _lancarBebida : null,
    );
  }

  Widget _buildBotaoCancelar() {
    // Cancela o lancamento do bar sem enviar nada para o banco.

    // Habilita o botao apenas quando reserva e bebida foram selecionadas.
    final habilitado = reservaSelecionada != null && bebidaSelecionada != null;
    return BotaoAcaoSecundaria(
      label: 'Cancelar Lançamento',
      icon: Icons.close,
      onPressed: habilitado ? _cancelarLancamento : null,
      foregroundColor: Colors.red.shade700,
      borderColor: Colors.red.shade300,
    );
  }
}
