import 'package:bravo_restaurante/models/reserva.dart';
import 'package:bravo_restaurante/services/reserva_service.dart';
import 'package:flutter/material.dart';

class ReservaViewModel extends ChangeNotifier {
  // Service responsavel por consultar reservas e contas vinculadas.
  final ReservaService _reservaService = ReservaService();

  // Estados observados pelos dropdowns de reserva nas telas.
  bool isLoading = false;
  String? mensagemErro;

  // Reservas abertas que podem receber pedido, bebida ou fechamento de conta.
  List<Reserva> reservas = [];

  Future<void> carregarReservasAbertas() async {
    // Sinaliza carregamento antes de buscar dados na API.
    isLoading = true;
    mensagemErro = null;
    notifyListeners();

    try {
      // Busca reservas abertas que ainda possuem conta aberta.
      reservas = await _reservaService.carregarReservasAbertas();

      isLoading = false;
      notifyListeners();
      debugPrint('Reservas abertas carregadas: ${reservas.length}');
    } catch (e) {
      mensagemErro = 'Erro ao carregar reservas: $e';
      isLoading = false;
      notifyListeners();
    }
  }

  void limpar() {
    // Limpa a selecao/lista local quando a tela precisa reiniciar o estado.
    reservas = [];
    mensagemErro = null;
    notifyListeners();
  }
}
