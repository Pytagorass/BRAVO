import 'package:bravo_restaurante/models/usuario.dart';

class MobileAccessControl {
  const MobileAccessControl._();

  static bool isFullAccess(Usuario? usuario) {
    final perfil = _perfil(usuario);
    return perfil == 'gerente' || perfil == 'administrador' || perfil == 'admin';
  }

  static bool canLancamentoConsumo(Usuario? usuario) {
    return isFullAccess(usuario) || _perfil(usuario) == 'consumo';
  }

  static bool canLavanderia(Usuario? usuario) {
    return isFullAccess(usuario) || _perfil(usuario) == 'lavanderia';
  }

  static bool canVerConta(Usuario? usuario) {
    final perfil = _perfil(usuario);
    return isFullAccess(usuario) ||
        perfil == 'consumo' ||
        perfil == 'lavanderia';
  }

  static bool canFecharConta(Usuario? usuario) {
    return isFullAccess(usuario) || _perfil(usuario) == 'consumo';
  }

  static bool hasAnyMobileAccess(Usuario? usuario) {
    return canLancamentoConsumo(usuario) ||
        canLavanderia(usuario) ||
        canVerConta(usuario) ||
        canFecharConta(usuario);
  }

  static String _perfil(Usuario? usuario) {
    final tipo = usuario?.tipoUsuario ?? '';
    return _normalizar(tipo);
  }

  static String _normalizar(String valor) {
    return valor.trim().toLowerCase().replaceAll(RegExp(r'\s+'), '_');
  }
}
