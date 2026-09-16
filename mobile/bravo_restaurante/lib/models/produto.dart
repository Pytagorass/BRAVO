// Representa um produto cadastrado no banco.
// Pode ser bebida, produto da lojinha ou outra categoria usada pelos dropdowns.
class Produto {
  // Campos principais da tabela produto.
  final String idProduto;
  final String nomeProduto;
  final String categoria;
  final String origem;
  final double preco;
  final bool ativo;

  Produto({
    required this.idProduto,
    required this.nomeProduto,
    required this.categoria,
    required this.origem,
    required this.preco,
    required this.ativo,
  });

  // Converte o Map retornado pela API em Produto.
  factory Produto.fromMap(Map<String, dynamic> map) {
    final ativoValue = map['ativo'];
    return Produto(
      idProduto: (map['id_produto'] ?? '').toString(),
      nomeProduto: map['nome_produto'] ?? '',
      categoria: map['nome_categoria'] ?? map['categoria'] ?? '',
      origem: map['tipo_categoria'] ?? map['origem'] ?? 'Restaurante',
      preco:
          (map['preco_atual'] as num?)?.toDouble() ??
          (map['preco'] as num?)?.toDouble() ??
          0.0,
      ativo: ativoValue == true || ativoValue == 'Ativo',
    );
  }

  // Converte Produto em Map usando os nomes das colunas do banco.
  Map<String, dynamic> toMap() {
    return {
      'id_produto': idProduto,
      'nome_produto': nomeProduto,
      'categoria': categoria,
      'origem': origem,
      'preco': preco,
      'ativo': ativo,
    };
  }
}
