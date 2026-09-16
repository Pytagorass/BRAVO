import 'package:bravo_restaurante/models/usuario.dart';
import 'package:bravo_restaurante/services/usuario_service.dart';
import 'package:flutter/material.dart';

class UsuarioViewModel extends ChangeNotifier {
  final UsuarioService _usuarioService = UsuarioService();

  bool isLoading = false;
  String? mensagemErro;
  Usuario? usuarioLogado;

  bool get estaLogado => usuarioLogado != null;

  Future<bool> login({required String email, required String senha}) async {
    isLoading = true;
    mensagemErro = null;
    notifyListeners();

    try {
      usuarioLogado = await _usuarioService.login(email: email, senha: senha);
      isLoading = false;
      notifyListeners();
      return true;
    } catch (e) {
      mensagemErro = 'Erro ao realizar login: $e';
      isLoading = false;
      notifyListeners();
      return false;
    }
  }

  void logout() {
    _usuarioService.logout();
    usuarioLogado = null;
    mensagemErro = null;
    notifyListeners();
  }
}
