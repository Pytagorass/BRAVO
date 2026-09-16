import 'package:bravo_restaurante/models/usuario.dart';
import 'package:bravo_restaurante/services/django_api_client.dart';

class UsuarioService {
  final DjangoApiClient _api = DjangoApiClient.instance;

  Future<Usuario> login({required String email, required String senha}) async {
    final response = await _api.post(
      '/login/',
      body: {'email': email, 'senha': senha},
    );

    final data = Map<String, dynamic>.from(response as Map);
    final token = data['token']?.toString();
    if (token == null || token.isEmpty) {
      throw const ApiException('Token nao retornado pela API.');
    }

    _api.setToken(token);

    final usuarioMap = Map<String, dynamic>.from(data['usuario'] as Map);
    return Usuario.fromMap(usuarioMap);
  }

  void logout() {
    _api.clearToken();
  }
}
