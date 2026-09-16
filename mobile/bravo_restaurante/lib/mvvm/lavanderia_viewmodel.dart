import 'package:bravo_restaurante/models/lavanderia.dart';
import 'package:bravo_restaurante/models/reserva.dart';
import 'package:bravo_restaurante/services/lavanderia_service.dart';
import 'package:flutter/material.dart';

class LavanderiaViewModel extends ChangeNotifier {
  final LavanderiaService _lavanderiaService = LavanderiaService();

  bool isLoading = false;
  bool isSaving = false;
  String? mensagemErro;
  List<CategoriaLavanderia> categorias = [];
  List<ServicoLavanderia> servicos = [];

  Future<void> carregarCatalogo() async {
    isLoading = true;
    mensagemErro = null;
    notifyListeners();

    try {
      categorias = await _lavanderiaService.carregarCategorias();
      servicos = await _lavanderiaService.carregarServicos();
    } catch (e) {
      mensagemErro = 'Erro ao carregar lavanderia: $e';
      debugPrint(mensagemErro);
    } finally {
      isLoading = false;
      notifyListeners();
    }
  }

  Future<bool> criarOrdem({
    required Reserva reserva,
    required List<ItemLavanderiaTemporario> itens,
    String? observacao,
  }) async {
    if (itens.isEmpty) {
      mensagemErro = 'Adicione pelo menos uma peca.';
      notifyListeners();
      return false;
    }

    isSaving = true;
    mensagemErro = null;
    notifyListeners();

    try {
      await _lavanderiaService.criarOrdem(
        reserva: reserva,
        itens: itens,
        observacao: observacao,
      );

      isSaving = false;
      notifyListeners();
      return true;
    } catch (e) {
      mensagemErro = 'Erro ao criar ordem de lavanderia: $e';
      debugPrint(mensagemErro);
      isSaving = false;
      notifyListeners();
      return false;
    }
  }
}
