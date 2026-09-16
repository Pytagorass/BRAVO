import 'package:bravo_restaurante/models/item_pedido.dart';

// Representa um pedido gravado na tabela pedido.
// O pedido pertence a uma ContaConsumo e pode ter varios itens.
class Pedido {
  // Identificadores principais da tabela pedido.
  final String idPedido;
  final String idConta;
  final String idUsuario;

  // Status, observacao opcional e total financeiro do pedido.
  final String statusPedido;
  final String? observacao;
  final double totalPedido;

  // Data de criacao gerada pelo banco.
  final DateTime? createdAt;

  // Itens relacionados quando a consulta inclui item_pedido.
  final List<ItemPedido> itens;

  Pedido({
    required this.idPedido,
    required this.idConta,
    required this.idUsuario,
    required this.statusPedido,
    required this.totalPedido,
    this.observacao,
    this.createdAt,
    this.itens = const [],
  });

  // Converte o Map retornado pela API em Pedido.
  factory Pedido.fromMap(Map<String, dynamic> map) {
    final itensMap = map['item_pedido'] as List<dynamic>? ?? [];

    return Pedido(
      idPedido: map['id_pedido'] ?? '',
      idConta: map['id_conta'] ?? '',
      idUsuario: map['id_usuario'] ?? '',
      statusPedido: map['status_pedido'] ?? '',
      observacao: map['observacao'],
      totalPedido: (map['total_pedido'] as num?)?.toDouble() ?? 0.0,
      createdAt: DateTime.tryParse(map['created_at']?.toString() ?? ''),
      itens: itensMap
          .map((item) => ItemPedido.fromMap(item as Map<String, dynamic>))
          .toList(),
    );
  }

  // Converte Pedido em Map usando os nomes das colunas do banco.
  Map<String, dynamic> toMap() {
    return {
      'id_pedido': idPedido,
      'id_conta': idConta,
      'id_usuario': idUsuario,
      'status_pedido': statusPedido,
      'observacao': observacao,
      'total_pedido': totalPedido,
      'created_at': createdAt?.toIso8601String(),
    };
  }

  // Monta o Map usado no insert da tabela pedido.
  // id_pedido e created_at ficam fora porque sao gerados pelo banco.
  Map<String, dynamic> toInsertMap() {
    return {
      'id_conta': idConta,
      'id_usuario': idUsuario,
      'status_pedido': statusPedido,
      'observacao': observacao,
      'total_pedido': totalPedido,
    };
  }
}
