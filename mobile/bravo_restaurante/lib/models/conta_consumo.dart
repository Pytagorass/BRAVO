import 'package:bravo_restaurante/models/lavanderia.dart';

// Representa a conta de consumo de uma reserva.
// Junta total, status e os consumos carregados em lojinha, bebidas e lavanderia.
class ContaConsumo {
  // Identificacao da conta e da reserva dona dessa conta.
  final String idConta;
  final String idReserva;

  // Total e status atuais calculados/armazenados no banco.
  final double totalAcumulado;
  final String statusConta;

  // Listas detalhadas usadas pela tela Conta do Hospede.
  final List<PedidoConta> pedidos;
  final List<BebidaConta> bebidas;
  final List<OrdemLavanderia> lavanderias;

  ContaConsumo({
    required this.idConta,
    required this.idReserva,
    required this.totalAcumulado,
    required this.statusConta,
    required this.pedidos,
    required this.bebidas,
    required this.lavanderias,
  });

  // Cria uma ContaConsumo a partir do Map da tabela conta_consumo.
  factory ContaConsumo.fromMap(
    Map<String, dynamic> map, {
    List<PedidoConta> pedidos = const [],
    List<BebidaConta> bebidas = const [],
    List<OrdemLavanderia> lavanderias = const [],
  }) {
    // A conta vem da tabela conta_consumo; pedidos e bebidas são carregados
    // separadamente pelo ViewModel para simplificar as consultas.
    return ContaConsumo(
      idConta: (map['id_conta'] ?? '').toString(),
      idReserva: (map['id_reserva'] ?? map['fk_reserva'] ?? '').toString(),
      totalAcumulado: (map['total_acumulado'] as num?)?.toDouble() ?? 0.0,
      statusConta: map['status_conta'] ?? '',
      pedidos: pedidos,
      bebidas: bebidas,
      lavanderias: lavanderias,
    );
  }
}

// Representa um pedido exibido dentro da conta do hospede.
class PedidoConta {
  // Dados principais da tabela pedido.
  final String idPedido;
  final String statusPedido;
  final String observacao;
  final double totalPedido;
  final DateTime? createdAt;

  // Itens ligados ao pedido pelo relacionamento item_pedido.
  final List<ItemPedidoConta> itens;

  PedidoConta({
    required this.idPedido,
    required this.statusPedido,
    required this.observacao,
    required this.totalPedido,
    this.createdAt,
    required this.itens,
  });

  // Converte a venda retornada pela API, incluindo a lista de itens.
  factory PedidoConta.fromMap(Map<String, dynamic> map) {
    // item_pedido chega como lista aninhada na consulta do PostgREST.
    final itensMap =
        map['item_pedido'] as List<dynamic>? ??
        map['itens'] as List<dynamic>? ??
        [];

    return PedidoConta(
      idPedido: (map['id_pedido'] ?? map['id_venda'] ?? '').toString(),
      statusPedido: map['status_pedido'] ?? map['status_venda'] ?? '',
      observacao: map['observacao'] ?? '',
      totalPedido:
          (map['total_pedido'] as num?)?.toDouble() ??
          (map['total_venda'] as num?)?.toDouble() ??
          0.0,
      createdAt: DateTime.tryParse(
        (map['created_at'] ?? map['dt_criacao'])?.toString() ?? '',
      ),
      itens: itensMap
          .map((item) => ItemPedidoConta.fromMap(item as Map<String, dynamic>))
          .toList(),
    );
  }
}

// Representa cada produto consumido dentro de um pedido.
class ItemPedidoConta {
  // Dados exibidos na lista expandida do pedido.
  final String nomeProduto;
  final int quantidade;
  final double valorUnitario;
  final double subtotal;

  ItemPedidoConta({
    required this.nomeProduto,
    required this.quantidade,
    required this.valorUnitario,
    required this.subtotal,
  });

  // Le o item e tambem o produto relacionado para obter o nome.
  factory ItemPedidoConta.fromMap(Map<String, dynamic> map) {
    // O nome do produto vem do relacionamento produto:id_produto.
    final produto = map['produto'] as Map<String, dynamic>? ?? {};

    return ItemPedidoConta(
      nomeProduto: map['nome_produto'] ?? produto['nome_produto'] ?? 'Produto',
      quantidade: map['quantidade'] ?? 0,
      valorUnitario: (map['valor_unitario'] as num?)?.toDouble() ?? 0.0,
      subtotal: (map['subtotal'] as num?)?.toDouble() ?? 0.0,
    );
  }
}

// Representa uma bebida lancada diretamente na conta, fora de pedido.
class BebidaConta {
  // Dados exibidos no card/list tile de bebidas da conta.
  final String nomeProduto;
  final int quantidade;
  final double valorUnitario;
  final double subtotal;
  final String observacao;
  final DateTime? createdAt;

  BebidaConta({
    required this.nomeProduto,
    required this.quantidade,
    required this.valorUnitario,
    required this.subtotal,
    required this.observacao,
    this.createdAt,
  });

  // Le a bebida e o produto relacionado retornados pela API.
  factory BebidaConta.fromMap(Map<String, dynamic> map) {
    // Bebidas são lançamentos diretos na conta, mas também referenciam produto.
    final produto = map['produto'] as Map<String, dynamic>? ?? {};

    return BebidaConta(
      nomeProduto: map['nome_produto'] ?? produto['nome_produto'] ?? 'Bebida',
      quantidade: map['quantidade'] ?? 0,
      valorUnitario: (map['valor_unitario'] as num?)?.toDouble() ?? 0.0,
      subtotal: (map['subtotal'] as num?)?.toDouble() ?? 0.0,
      observacao: map['observacao'] ?? '',
      createdAt: DateTime.tryParse(
        (map['created_at'] ?? map['dt_criacao'])?.toString() ?? '',
      ),
    );
  }
}
