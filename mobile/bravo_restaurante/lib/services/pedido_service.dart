import 'package:bravo_restaurante/models/item_pedido_temporario.dart';
import 'package:bravo_restaurante/models/reserva.dart';
import 'package:bravo_restaurante/services/django_api_client.dart';

class PedidoService {
  final DjangoApiClient _api = DjangoApiClient.instance;

  Future<void> gravarContaConsumo({
    required Reserva reserva,
    required List<ItemPedidoTemporario> itens,
    required double total,
    required String idUsuario,
    String? origem,
    String? observacao,
  }) async {
    final origemVenda = origem ?? itens.first.produto.origem;

    await _api.post(
      '/consumo/vendas/',
      body: {
        'fk_reserva': int.parse(reserva.idReserva),
        'origem': origemVenda,
        'observacao': observacao,
        'itens': itens
            .map(
              (item) => {
                'fk_produto': int.parse(item.produto.idProduto),
                'quantidade': item.quantidade,
                'observacao': item.observacao.trim().isEmpty
                    ? null
                    : item.observacao.trim(),
              },
            )
            .toList(),
      },
    );
  }
}
