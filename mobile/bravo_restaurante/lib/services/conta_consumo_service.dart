import 'package:bravo_restaurante/models/conta_consumo.dart';
import 'package:bravo_restaurante/models/reserva.dart';
import 'package:bravo_restaurante/models/resumo_fechamento_conta.dart';
import 'package:bravo_restaurante/services/django_api_client.dart';

class ContaConsumoService {
  final DjangoApiClient _api = DjangoApiClient.instance;

  Future<ContaConsumo?> carregarContaDaReserva(Reserva reserva) async {
    if (reserva.idConta.isEmpty) {
      return null;
    }

    final contaMap = await _carregarContaPorId(reserva.idConta);
    final vendas = _extrairVendas(contaMap);

    return ContaConsumo.fromMap(
      contaMap,
      pedidos: _mapearPedidos(vendas),
      bebidas: _mapearBebidas(vendas),
    );
  }

  Future<ResumoFechamentoConta> carregarResumoFechamento(
    Reserva reserva,
  ) async {
    final contaMap = await _carregarContaPorId(reserva.idConta);
    final vendas = _extrairVendas(contaMap);

    return ResumoFechamentoConta(
      pedidos: _mapearPedidosResumo(vendas),
      bebidas: _mapearBebidasResumo(vendas),
      totalConta: (contaMap['total_acumulado'] as num?)?.toDouble() ?? 0.0,
    );
  }

  Future<void> fecharContaDaReserva({
    required String idConta,
    required String idReserva,
  }) async {
    await _api.post('/consumo/contas/$idConta/fechar/');
  }

  Future<Map<String, dynamic>> _carregarContaPorId(String idConta) async {
    final response = await _api.get('/consumo/contas/$idConta/');
    return Map<String, dynamic>.from(response as Map);
  }

  List<Map<String, dynamic>> _extrairVendas(Map<String, dynamic> contaMap) {
    final vendas = contaMap['vendas'] as List<dynamic>? ?? [];
    return vendas
        .map((venda) => Map<String, dynamic>.from(venda as Map))
        .where((venda) => venda['status_venda'] != 'Cancelada')
        .toList();
  }

  List<PedidoConta> _mapearPedidos(List<Map<String, dynamic>> vendas) {
    return vendas
        .where((venda) => !_vendaSomenteBebidas(venda))
        .map((venda) => PedidoConta.fromMap(venda))
        .toList();
  }

  List<BebidaConta> _mapearBebidas(List<Map<String, dynamic>> vendas) {
    return vendas.where(_vendaSomenteBebidas).expand((venda) {
      final itens = venda['itens'] as List<dynamic>? ?? [];
      return itens.map((item) {
        final itemMap = Map<String, dynamic>.from(item as Map);
        return BebidaConta.fromMap({
          ...itemMap,
          'observacao': venda['observacao'],
          'dt_criacao': venda['dt_criacao'],
        });
      });
    }).toList();
  }

  List<PedidoResumoConta> _mapearPedidosResumo(
    List<Map<String, dynamic>> vendas,
  ) {
    return vendas
        .where((venda) => !_vendaSomenteBebidas(venda))
        .map((venda) => PedidoResumoConta.fromMap(venda))
        .toList();
  }

  List<BebidaResumoConta> _mapearBebidasResumo(
    List<Map<String, dynamic>> vendas,
  ) {
    return vendas.where(_vendaSomenteBebidas).expand((venda) {
      final itens = venda['itens'] as List<dynamic>? ?? [];
      return itens.map((item) {
        final itemMap = Map<String, dynamic>.from(item as Map);
        return BebidaResumoConta.fromMap({
          ...itemMap,
          'dt_criacao': venda['dt_criacao'],
        });
      });
    }).toList();
  }

  bool _vendaSomenteBebidas(Map<String, dynamic> venda) {
    final itens = venda['itens'] as List<dynamic>? ?? [];
    if (itens.isEmpty) return false;

    return itens.every((item) {
      final itemMap = Map<String, dynamic>.from(item as Map);
      final categoria =
          itemMap['nome_categoria']?.toString().toLowerCase() ?? '';
      return categoria.contains('bebida');
    });
  }
}
