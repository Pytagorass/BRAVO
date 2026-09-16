import 'package:bravo_restaurante/models/produto.dart';

// Representa um item antes de o pedido ser confirmado no banco.
// Ele fica apenas em memoria enquanto o usuario monta o pedido na tela.
class ItemPedidoTemporario {
  // Produto escolhido no dropdown.
  final Produto produto;

  // Quantidade e observacao informadas pelo usuario.
  final int quantidade;
  final String observacao;

  ItemPedidoTemporario({
    required this.produto,
    required this.quantidade,
    required this.observacao,
  });

  // Calcula o subtotal localmente para exibir antes da gravacao.
  double get subtotal {
    return produto.preco * quantidade;
  }

  // Monta o payload esperado pela tabela item_pedido.
  // O id_pedido so existe depois que o pedido e criado no banco.
  Map<String, dynamic> toMap({String? idPedido}) {
    // Campos que correspondem as colunas da tabela item_pedido.
    final map = {
      'id_produto': produto.idProduto,
      'quantidade': quantidade,
      'valor_unitario': produto.preco,
      'subtotal': subtotal,
    };

    // Inclui o id do pedido somente quando ele ja foi criado na API.
    if (idPedido != null) {
      map['id_pedido'] = idPedido;
    }

    return map;
  }

  // Monta o Map usado no insert da tabela item_pedido.
  // Como o item ainda e temporario, ele nao envia id_item nem created_at.
  Map<String, dynamic> toInsertMap({required String idPedido}) {
    return {
      'id_pedido': idPedido,
      'id_produto': produto.idProduto,
      'quantidade': quantidade,
      'valor_unitario': produto.preco,
      'subtotal': subtotal,
    };
  }
}
