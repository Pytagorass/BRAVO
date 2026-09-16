import 'package:bravo_restaurante/models/item_pedido_temporario.dart';
import 'package:bravo_restaurante/models/reserva.dart';
import 'package:bravo_restaurante/services/pedido_service.dart';
import 'package:flutter/material.dart';

class PedidoViewModel extends ChangeNotifier {
  final PedidoService _pedidoService = PedidoService();

  bool isLoading = false;
  String? mensagemErro;

  Future<bool> gravarContaConsumo({
    required Reserva reserva,
    required List<ItemPedidoTemporario> itens,
    required double total,
    required String idUsuario,
    String? origem,
    String? observacao,
  }) async {
    if (itens.isEmpty) {
      mensagemErro = 'Adicione pelo menos um item ao pedido.';
      notifyListeners();
      return false;
    }

    isLoading = true;
    mensagemErro = null;
    notifyListeners();

    try {
      await _pedidoService.gravarContaConsumo(
        reserva: reserva,
        itens: itens,
        total: total,
        idUsuario: idUsuario,
        origem: origem,
        observacao: observacao,
      );

      isLoading = false;
      notifyListeners();
      return true;
    } catch (e) {
      mensagemErro = 'Erro ao gravar consumo: $e';
      debugPrint(mensagemErro);
      isLoading = false;
      notifyListeners();
      return false;
    }
  }
}
