import 'package:bravo_restaurante/models/produto.dart';
import 'package:bravo_restaurante/services/django_api_client.dart';

class ProdutoService {
  final DjangoApiClient _api = DjangoApiClient.instance;

  Future<List<Produto>> carregarProdutosAtivos({String? origem}) async {
    final response = await _api.get(
      '/consumo/produtos/',
      queryParameters: {
        'ativo': 'Ativo',
        if (origem != null && origem != 'Todos') 'origem': origem,
      },
    );

    return (response as List)
        .map((item) => Produto.fromMap(Map<String, dynamic>.from(item as Map)))
        .toList();
  }
}
