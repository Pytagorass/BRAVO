// Representa um usuario cadastrado no banco e usado no login.
class Usuario {
  // Campos principais da tabela usuario.
  final String idUsuario;
  final String nomeUsuario;
  final String emailUsuario;
  final String senha;
  final String tipoUsuario;
  final bool ativo;

  Usuario({
    required this.idUsuario,
    required this.nomeUsuario,
    required this.emailUsuario,
    required this.senha,
    required this.tipoUsuario,
    required this.ativo,
  });

  // Converte o Map retornado pela API em Usuario.
  factory Usuario.fromMap(Map<String, dynamic> map) {
    final ativoValue = map['ativo'];
    return Usuario(
      idUsuario: (map['id_usuario'] ?? map['id'] ?? '').toString(),
      nomeUsuario: map['nome_usuario'] ?? map['nome'] ?? '',
      emailUsuario: map['email_usuario'] ?? map['email'] ?? '',
      senha: map['senha'] ?? '',
      tipoUsuario: map['tipo_usuario'] ?? map['tipo'] ?? '',
      ativo: ativoValue == null || ativoValue == true || ativoValue == 'Ativo',
    );
  }

  // Converte Usuario em Map usando os nomes das colunas do banco.
  Map<String, dynamic> toMap() {
    return {
      'id_usuario': idUsuario,
      'nome_usuario': nomeUsuario,
      'email_usuario': emailUsuario,
      'senha': senha,
      'tipo_usuario': tipoUsuario,
      'ativo': ativo,
    };
  }
}
