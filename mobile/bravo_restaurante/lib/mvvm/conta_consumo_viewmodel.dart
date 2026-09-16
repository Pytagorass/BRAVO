import 'package:bravo_restaurante/models/conta_consumo.dart';
import 'package:bravo_restaurante/models/reserva.dart';
import 'package:bravo_restaurante/models/resumo_fechamento_conta.dart';
import 'package:bravo_restaurante/services/conta_consumo_service.dart';
import 'package:flutter/material.dart';
import 'package:flutter/scheduler.dart';

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

  void _notificarComSeguranca() {
    final schedulerPhase = SchedulerBinding.instance.schedulerPhase;
    final podeNotificarAgora =
        schedulerPhase == SchedulerPhase.idle ||
        schedulerPhase == SchedulerPhase.postFrameCallbacks;

    if (podeNotificarAgora) {
      notifyListeners();
      return;
    }

    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (hasListeners) {
        notifyListeners();
      }
    });
  }

  Future<void> carregarContaDaReserva(Reserva reserva) async {
    // Limpa dados antigos antes de carregar a conta da nova reserva selecionada.
    isLoading = true;
    mensagemErro = null;
    conta = null;
    _notificarComSeguranca();

    try {
      conta = await _contaConsumoService.carregarContaDaReserva(reserva);

      if (conta == null) {
        mensagemErro = 'Nenhuma conta de consumo encontrada para esta reserva.';
        isLoading = false;
        _notificarComSeguranca();
        return;
      }

      isLoading = false;
      _notificarComSeguranca();
    } catch (e) {
      mensagemErro = 'Erro ao carregar conta de consumo: $e';
      debugPrint(mensagemErro);
      isLoading = false;
      _notificarComSeguranca();
    }
  }

  void limpar({bool notificar = true}) {
    // Remove a conta atual quando nenhuma reserva esta selecionada.
    conta = null;
    mensagemErro = null;
    if (notificar) {
      _notificarComSeguranca();
    }
  }

  Future<void> carregarResumoFechamento(Reserva reserva) async {
    carregandoResumoFechamento = true;
    mensagemErroFechamento = null;
    resumoFechamento = null;
    _notificarComSeguranca();

    try {
      resumoFechamento = await _contaConsumoService.carregarResumoFechamento(
        reserva,
      );

      carregandoResumoFechamento = false;
      _notificarComSeguranca();
    } catch (e) {
      mensagemErroFechamento = 'Erro ao carregar conta: $e';
      carregandoResumoFechamento = false;
      _notificarComSeguranca();
    }
  }

  Future<bool> fecharContaDaReserva(Reserva reserva) async {
    mensagemErroFechamento = null;
    _notificarComSeguranca();

    try {
      await _contaConsumoService.fecharContaDaReserva(
        idConta: reserva.idConta,
        idReserva: reserva.idReserva,
      );

      limparResumoFechamento();
      return true;
    } catch (e) {
      mensagemErroFechamento = 'Erro ao fechar conta: $e';
      _notificarComSeguranca();
      return false;
    }
  }

  void limparResumoFechamento() {
    resumoFechamento = null;
    mensagemErroFechamento = null;
    carregandoResumoFechamento = false;
    _notificarComSeguranca();
  }
}
