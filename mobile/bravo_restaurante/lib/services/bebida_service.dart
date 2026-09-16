import 'package:bravo_restaurante/services/django_api_client.dart';

class BebidaService {
  final DjangoApiClient _api = DjangoApiClient.instance;

  Future<void> lancarBebidaNaConta({
    required String idReserva,
    required String idProduto,
    required String idUsuario,
    required int quantidade,
    required double valorUnitario,
    String? observacao,
  }) async {
    await _api.post(
      '/consumo/vendas/',
      body: {
        'fk_reserva': int.parse(idReserva),
        'origem': 'Restaurante',
        'observacao': observacao,
        'itens': [
          {
            'fk_produto': int.parse(idProduto),
            'quantidade': quantidade,
            'observacao': observacao,
          },
        ],
      },
    );
  }

  Future<List<Map<String, dynamic>>> buscarBebidasPorConta(
    String idConta,
  ) async {
    final response = await _api.get('/consumo/contas/$idConta/');
    final conta = Map<String, dynamic>.from(response as Map);
    final vendas = conta['vendas'] as List<dynamic>? ?? [];
    return vendas.expand((venda) {
      final vendaMap = Map<String, dynamic>.from(venda as Map);
      final itens = vendaMap['itens'] as List<dynamic>? ?? [];
      return itens
          .where((item) {
            final itemMap = Map<String, dynamic>.from(item as Map);
            final categoria = itemMap['nome_categoria']?.toString() ?? '';
            return categoria.toLowerCase().contains('bebida');
          })
          .map((item) => Map<String, dynamic>.from(item as Map));
    }).toList();
  }
}
