class ResumoFechamentoConta {
  final List<PedidoResumoConta> pedidos;
  final List<BebidaResumoConta> bebidas;
  final double totalConta;

  const ResumoFechamentoConta({
    required this.pedidos,
    required this.bebidas,
    required this.totalConta,
  });
}

class PedidoResumoConta {
  final double totalPedido;
  final DateTime? createdAt;
  final List<ItemResumoConta> itens;

  const PedidoResumoConta({
    required this.totalPedido,
    required this.createdAt,
    required this.itens,
  });

  factory PedidoResumoConta.fromMap(Map<String, dynamic> map) {
    final itensMap =
        map['item_pedido'] as List<dynamic>? ??
        map['itens'] as List<dynamic>? ??
        [];

    return PedidoResumoConta(
      totalPedido:
          (map['total_pedido'] as num?)?.toDouble() ??
          (map['total_venda'] as num?)?.toDouble() ??
          0.0,
      createdAt: DateTime.tryParse(
        (map['created_at'] ?? map['dt_criacao'])?.toString() ?? '',
      ),
      itens: itensMap
          .map((item) => ItemResumoConta.fromMap(item as Map<String, dynamic>))
          .toList(),
    );
  }
}

class ItemResumoConta {
  final String nomeProduto;
  final int quantidade;
  final double subtotal;

  const ItemResumoConta({
    required this.nomeProduto,
    required this.quantidade,
    required this.subtotal,
  });

  factory ItemResumoConta.fromMap(Map<String, dynamic> map) {
    final produto = map['produto'] as Map<String, dynamic>? ?? {};

    return ItemResumoConta(
      nomeProduto: map['nome_produto'] ?? produto['nome_produto'] ?? 'Produto',
      quantidade: map['quantidade'] ?? 0,
      subtotal: (map['subtotal'] as num?)?.toDouble() ?? 0.0,
    );
  }
}

class BebidaResumoConta {
  final String nomeProduto;
  final int quantidade;
  final double subtotal;
  final DateTime? createdAt;

  const BebidaResumoConta({
    required this.nomeProduto,
    required this.quantidade,
    required this.subtotal,
    required this.createdAt,
  });

  factory BebidaResumoConta.fromMap(Map<String, dynamic> map) {
    final produto = map['produto'] as Map<String, dynamic>? ?? {};

    return BebidaResumoConta(
      nomeProduto: map['nome_produto'] ?? produto['nome_produto'] ?? 'Bebida',
      quantidade: map['quantidade'] ?? 0,
      subtotal: (map['subtotal'] as num?)?.toDouble() ?? 0.0,
      createdAt: DateTime.tryParse(
        (map['created_at'] ?? map['dt_criacao'])?.toString() ?? '',
      ),
    );
  }
}
