import 'package:bravo_restaurante/models/reserva.dart';
import 'package:bravo_restaurante/services/django_api_client.dart';

class ReservaService {
  final DjangoApiClient _api = DjangoApiClient.instance;

  Future<List<Reserva>> carregarReservasAbertas() async {
    final response = await _api.get('/consumo/reservas-abertas/');

    return (response as List)
        .map((item) => Reserva.fromMap(Map<String, dynamic>.from(item as Map)))
        .toList();
  }
}
