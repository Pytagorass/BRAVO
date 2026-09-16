import 'dart:convert';

import 'package:http/http.dart' as http;

class ApiException implements Exception {
  final String message;
  final String code;
  final int? statusCode;

  const ApiException(
    this.message, {
    this.code = 'ERRO_INTERNO',
    this.statusCode,
  });

  @override
  String toString() => message;
}

class DjangoApiClient {
  DjangoApiClient._();

  static final DjangoApiClient instance = DjangoApiClient._();

  static const String _defaultBaseUrl = 'http://127.0.0.1:8000/api';

  final http.Client _client = http.Client();

  String baseUrl = const String.fromEnvironment(
    'BRAVO_API_URL',
    defaultValue: _defaultBaseUrl,
  );

  String? _token;

  bool get isAuthenticated => _token != null && _token!.isNotEmpty;

  void setToken(String token) {
    _token = token;
  }

  void clearToken() {
    _token = null;
  }

  Future<dynamic> get(String path, {Map<String, dynamic>? queryParameters}) {
    return _send('GET', path, queryParameters: queryParameters);
  }

  Future<dynamic> post(String path, {Map<String, dynamic>? body}) {
    return _send('POST', path, body: body);
  }

  Future<dynamic> _send(
    String method,
    String path, {
    Map<String, dynamic>? queryParameters,
    Map<String, dynamic>? body,
  }) async {
    final uri = _buildUri(path, queryParameters);
    final headers = <String, String>{
      'Accept': 'application/json',
      'Content-Type': 'application/json',
      if (_token != null) 'Authorization': 'Bearer $_token',
    };

    late final http.Response response;
    if (method == 'GET') {
      response = await _client.get(uri, headers: headers);
    } else if (method == 'POST') {
      response = await _client.post(
        uri,
        headers: headers,
        body: jsonEncode(body ?? <String, dynamic>{}),
      );
    } else {
      throw const ApiException('Metodo HTTP nao suportado.');
    }

    return _parseResponse(response);
  }

  Uri _buildUri(String path, Map<String, dynamic>? queryParameters) {
    final normalizedBase = baseUrl.endsWith('/')
        ? baseUrl.substring(0, baseUrl.length - 1)
        : baseUrl;
    final normalizedPath = path.startsWith('/') ? path : '/$path';

    final uri = Uri.parse('$normalizedBase$normalizedPath');
    if (queryParameters == null || queryParameters.isEmpty) {
      return uri;
    }

    final params = <String, String>{};
    queryParameters.forEach((key, value) {
      if (value != null && value.toString().isNotEmpty) {
        params[key] = value.toString();
      }
    });

    return uri.replace(queryParameters: params);
  }

  dynamic _parseResponse(http.Response response) {
    dynamic payload;
    try {
      payload = response.body.isEmpty ? null : jsonDecode(response.body);
    } catch (_) {
      throw ApiException(
        'Resposta invalida da API.',
        code: 'INVALID_RESPONSE',
        statusCode: response.statusCode,
      );
    }

    if (response.statusCode < 200 || response.statusCode >= 300) {
      final error = payload is Map<String, dynamic> ? payload['error'] : null;
      if (error is Map<String, dynamic>) {
        throw ApiException(
          error['message']?.toString() ?? 'Falha ao processar requisicao.',
          code: error['code']?.toString() ?? 'ERRO_INTERNO',
          statusCode: response.statusCode,
        );
      }

      throw ApiException(
        'Falha ao processar requisicao.',
        statusCode: response.statusCode,
      );
    }

    if (payload is Map<String, dynamic> && payload['success'] == true) {
      return payload['data'];
    }

    if (payload is Map<String, dynamic> && payload['success'] == false) {
      final error = payload['error'];
      if (error is Map<String, dynamic>) {
        throw ApiException(
          error['message']?.toString() ?? 'Operacao nao pode ser concluida.',
          code: error['code']?.toString() ?? 'ERRO_INTERNO',
          statusCode: response.statusCode,
        );
      }
    }

    return payload;
  }
}
