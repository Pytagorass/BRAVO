// Representa um item ja gravado na tabela item_pedido.
// Cada item pertence a um pedido e aponta para um produto consumido.
class ItemPedido {
  // Chave propria da tabela item_pedido.
  final String idItem;

  // Relacionamentos com pedido e produto.
  final String idPedido;
  final String idProduto;

  // Quantidade e valores gravados para este item.
  final int quantidade;
  final double valorUnitario;
  final double subtotal;

  // Data de criacao gerada pelo banco.
  final DateTime? createdAt;

  ItemPedido({
    required this.idItem,
    required this.idPedido,
    required this.idProduto,
    required this.quantidade,
    required this.valorUnitario,
    required this.subtotal,
    this.createdAt,
  });

  // Converte o Map retornado pela API em ItemPedido.
  factory ItemPedido.fromMap(Map<String, dynamic> map) {
    return ItemPedido(
      idItem: map['id_item'] ?? '',
      idPedido: map['id_pedido'] ?? '',
      idProduto: map['id_produto'] ?? '',
      quantidade: map['quantidade'] ?? 0,
      valorUnitario: (map['valor_unitario'] as num?)?.toDouble() ?? 0.0,
      subtotal: (map['subtotal'] as num?)?.toDouble() ?? 0.0,
      createdAt: DateTime.tryParse(map['created_at']?.toString() ?? ''),
    );
  }

  // Converte ItemPedido em Map usando os nomes das colunas do banco.
  Map<String, dynamic> toMap() {
    return {
      'id_item': idItem,
      'id_pedido': idPedido,
      'id_produto': idProduto,
      'quantidade': quantidade,
      'valor_unitario': valorUnitario,
      'subtotal': subtotal,
      'created_at': createdAt?.toIso8601String(),
    };
  }

  // Monta o Map usado no insert da tabela item_pedido.
  // id_item e created_at ficam fora porque sao gerados pelo banco.
  Map<String, dynamic> toInsertMap() {
    return {
      'id_pedido': idPedido,
      'id_produto': idProduto,
      'quantidade': quantidade,
      'valor_unitario': valorUnitario,
      'subtotal': subtotal,
    };
  }
}
