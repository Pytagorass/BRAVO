import 'package:bravo_restaurante/services/bebida_service.dart';
import 'package:flutter/material.dart';

class BebidaViewModel extends ChangeNotifier {
  final BebidaService _bebidaService = BebidaService();

  bool isLoading = false;
  String? mensagemErro;

  Future<bool> lancarBebidaNaConta({
    required String idReserva,
    required String idProduto,
    required String idUsuario,
    required int quantidade,
    required double valorUnitario,
    String? observacao,
  }) async {
    isLoading = true;
    mensagemErro = null;
    notifyListeners();

    try {
      await _bebidaService.lancarBebidaNaConta(
        idReserva: idReserva,
        idProduto: idProduto,
        idUsuario: idUsuario,
        quantidade: quantidade,
        valorUnitario: valorUnitario,
        observacao: observacao,
      );

      isLoading = false;
      notifyListeners();
      return true;
    } catch (e) {
      mensagemErro = 'Erro ao lancar bebida: $e';
      isLoading = false;
      notifyListeners();
      return false;
    }
  }

  Future<List<Map<String, dynamic>>> buscarBebidasPorConta(
    String idConta,
  ) async {
    try {
      return await _bebidaService.buscarBebidasPorConta(idConta);
    } catch (e) {
      mensagemErro = 'Erro ao buscar bebidas da conta: $e';
      notifyListeners();
      return [];
    }
  }
}
