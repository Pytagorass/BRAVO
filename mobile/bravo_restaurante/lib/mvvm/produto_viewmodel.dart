import 'package:bravo_restaurante/models/produto.dart';
import 'package:bravo_restaurante/services/produto_service.dart';
import 'package:flutter/material.dart';

class ProdutoViewModel extends ChangeNotifier {
  final ProdutoService _produtoService = ProdutoService();

  bool isLoading = false;
  String? mensagemErro;
  List<Produto> produtos = [];

  Future<void> carregarProdutos({String? origem}) async {
    isLoading = true;
    mensagemErro = null;
    notifyListeners();

    try {
      produtos = await _produtoService.carregarProdutosAtivos(origem: origem);
      debugPrint('Produtos ativos carregados: ${produtos.length}');

      isLoading = false;
      notifyListeners();
    } catch (e) {
      debugPrint('Erro ao carregar produtos: $e');
      mensagemErro = 'Erro ao carregar produtos: $e';
      isLoading = false;
      notifyListeners();
    }
  }

  List<Produto> filtrarPorCategoria(String categoria) {
    return produtos.where((produto) => produto.categoria == categoria).toList();
  }

  void limparErro() {
    mensagemErro = null;
    notifyListeners();
  }
}
