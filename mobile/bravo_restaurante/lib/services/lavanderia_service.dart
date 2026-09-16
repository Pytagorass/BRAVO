import 'package:bravo_restaurante/models/lavanderia.dart';
import 'package:bravo_restaurante/models/reserva.dart';
import 'package:bravo_restaurante/services/django_api_client.dart';

class LavanderiaService {
  final DjangoApiClient _api = DjangoApiClient.instance;

  Future<List<CategoriaLavanderia>> carregarCategorias() async {
    final response = await _api.get('/consumo/lavanderia/categorias/');
    final categorias = response as List<dynamic>? ?? [];
    return categorias
        .map(
          (categoria) =>
              CategoriaLavanderia.fromMap(Map<String, dynamic>.from(categoria)),
        )
        .toList();
  }

  Future<List<ServicoLavanderia>> carregarServicos() async {
    final response = await _api.get('/consumo/lavanderia/servicos/');
    final servicos = response as List<dynamic>? ?? [];
    return servicos
        .map(
          (servico) =>
              ServicoLavanderia.fromMap(Map<String, dynamic>.from(servico)),
        )
        .toList();
  }

  Future<OrdemLavanderia> criarOrdem({
    required Reserva reserva,
    required List<ItemLavanderiaTemporario> itens,
    String? observacao,
  }) async {
    final response = await _api.post(
      '/consumo/lavanderia/ordens/',
      body: {
        'fk_reserva': int.parse(reserva.idReserva),
        'observacao': observacao?.trim().isEmpty == true
            ? null
            : observacao?.trim(),
        'itens': itens.map((item) => item.toApiMap()).toList(),
      },
    );

    return OrdemLavanderia.fromMap(Map<String, dynamic>.from(response as Map));
  }

  Future<void> atualizarStatus({
    required String idOrdem,
    required String status,
    String? observacao,
  }) async {
    await _api.post(
      '/consumo/lavanderia/ordens/$idOrdem/status/',
      body: {
        'status_ordem': status,
        'observacao': observacao?.trim().isEmpty == true
            ? null
            : observacao?.trim(),
      },
    );
  }
}
