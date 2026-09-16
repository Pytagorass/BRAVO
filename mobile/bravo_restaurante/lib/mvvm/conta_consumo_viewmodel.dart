import 'package:bravo_restaurante/models/conta_consumo.dart';
import 'package:bravo_restaurante/models/reserva.dart';
import 'package:bravo_restaurante/models/resumo_fechamento_conta.dart';
import 'package:bravo_restaurante/services/conta_consumo_service.dart';
import 'package:flutter/material.dart';

class ContaConsumoViewModel extends ChangeNotifier {
  // Service responsavel por consultar conta, pedidos e bebidas da reserva.
  final ContaConsumoService _contaConsumoService = ContaConsumoService();

  // Estados observados pela tela de conta do hospede.
  bool isLoading = false;
  String? mensagemErro;
  ContaConsumo? conta;

  // Estados observados pela tela de fechamento da conta.
  bool carregandoResumoFechamento = false;
  String? mensagemErroFechamento;
  ResumoFechamentoConta? resumoFechamento;

  Future<void> carregarContaDaReserva(Reserva reserva) async {
    // Limpa dados antigos antes de carregar a conta da nova reserva selecionada.
    isLoading = true;
    mensagemErro = null;
    conta = null;
    notifyListeners();

    try {
      conta = await _contaConsumoService.carregarContaDaReserva(reserva);

      if (conta == null) {
        mensagemErro = 'Nenhuma conta de consumo encontrada para esta reserva.';
        isLoading = false;
        notifyListeners();
        return;
      }

      isLoading = false;
      notifyListeners();
    } catch (e) {
      mensagemErro = 'Erro ao carregar conta de consumo: $e';
      debugPrint(mensagemErro);
      isLoading = false;
      notifyListeners();
    }
  }

  void limpar() {
    // Remove a conta atual quando nenhuma reserva esta selecionada.
    conta = null;
    mensagemErro = null;
    notifyListeners();
  }

  Future<void> carregarResumoFechamento(Reserva reserva) async {
    carregandoResumoFechamento = true;
    mensagemErroFechamento = null;
    resumoFechamento = null;
    notifyListeners();

    try {
      resumoFechamento = await _contaConsumoService.carregarResumoFechamento(
        reserva,
      );

      carregandoResumoFechamento = false;
      notifyListeners();
    } catch (e) {
      mensagemErroFechamento = 'Erro ao carregar conta: $e';
      carregandoResumoFechamento = false;
      notifyListeners();
    }
  }

  Future<bool> fecharContaDaReserva(Reserva reserva) async {
    mensagemErroFechamento = null;
    notifyListeners();

    try {
      await _contaConsumoService.fecharContaDaReserva(
        idConta: reserva.idConta,
        idReserva: reserva.idReserva,
      );

      limparResumoFechamento();
      return true;
    } catch (e) {
      mensagemErroFechamento = 'Erro ao fechar conta: $e';
      notifyListeners();
      return false;
    }
  }

  void limparResumoFechamento() {
    resumoFechamento = null;
    mensagemErroFechamento = null;
    carregandoResumoFechamento = false;
    notifyListeners();
  }
}
