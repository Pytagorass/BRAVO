class CategoriaLavanderia {
  final String idCategoria;
  final String nomeCategoria;
  final String descricao;
  final String ativo;
  final int ordemExibicao;

  const CategoriaLavanderia({
    required this.idCategoria,
    required this.nomeCategoria,
    required this.descricao,
    required this.ativo,
    required this.ordemExibicao,
  });

  factory CategoriaLavanderia.fromMap(Map<String, dynamic> map) {
    return CategoriaLavanderia(
      idCategoria: (map['id_categoria'] ?? '').toString(),
      nomeCategoria: map['nome_categoria'] ?? '',
      descricao: map['descricao'] ?? '',
      ativo: map['ativo'] ?? '',
      ordemExibicao: map['ordem_exibicao'] ?? 0,
    );
  }
}

class ServicoLavanderia {
  final String idServico;
  final String idCategoria;
  final String nomeCategoria;
  final String nomeServico;
  final String descricao;
  final double precoUnitario;
  final int prazoHoras;
  final String ativo;

  const ServicoLavanderia({
    required this.idServico,
    required this.idCategoria,
    required this.nomeCategoria,
    required this.nomeServico,
    required this.descricao,
    required this.precoUnitario,
    required this.prazoHoras,
    required this.ativo,
  });

  factory ServicoLavanderia.fromMap(Map<String, dynamic> map) {
    return ServicoLavanderia(
      idServico: (map['id_servico'] ?? '').toString(),
      idCategoria: (map['fk_categoria'] ?? map['id_categoria'] ?? '')
          .toString(),
      nomeCategoria: map['nome_categoria'] ?? '',
      nomeServico: map['nome_servico'] ?? '',
      descricao: map['descricao'] ?? '',
      precoUnitario: (map['preco_unitario'] as num?)?.toDouble() ?? 0.0,
      prazoHoras: map['prazo_horas'] ?? 24,
      ativo: map['ativo'] ?? '',
    );
  }
}

class ItemLavanderiaTemporario {
  final ServicoLavanderia servico;
  final int quantidade;
  final String observacao;

  const ItemLavanderiaTemporario({
    required this.servico,
    required this.quantidade,
    this.observacao = '',
  });

  double get subtotal => servico.precoUnitario * quantidade;

  Map<String, dynamic> toApiMap() {
    return {
      'fk_servico': int.parse(servico.idServico),
      'quantidade': quantidade,
      'observacao': observacao.trim().isEmpty ? null : observacao.trim(),
    };
  }
}

class OrdemLavanderia {
  final String idOrdem;
  final String statusOrdem;
  final double totalOrdem;
  final String observacao;
  final DateTime? dtRecebimento;
  final DateTime? dtPrevisaoEntrega;
  final DateTime? dtEntrega;
  final List<ItemOrdemLavanderia> itens;

  const OrdemLavanderia({
    required this.idOrdem,
    required this.statusOrdem,
    required this.totalOrdem,
    required this.observacao,
    required this.dtRecebimento,
    required this.dtPrevisaoEntrega,
    required this.dtEntrega,
    required this.itens,
  });

  factory OrdemLavanderia.fromMap(Map<String, dynamic> map) {
    final itensMap = map['itens'] as List<dynamic>? ?? [];

    return OrdemLavanderia(
      idOrdem: (map['id_ordem'] ?? '').toString(),
      statusOrdem: map['status_ordem'] ?? '',
      totalOrdem: (map['total_ordem'] as num?)?.toDouble() ?? 0.0,
      observacao: map['observacao'] ?? '',
      dtRecebimento: DateTime.tryParse(map['dt_recebimento']?.toString() ?? ''),
      dtPrevisaoEntrega: DateTime.tryParse(
        map['dt_previsao_entrega']?.toString() ?? '',
      ),
      dtEntrega: DateTime.tryParse(map['dt_entrega']?.toString() ?? ''),
      itens: itensMap
          .map(
            (item) =>
                ItemOrdemLavanderia.fromMap(Map<String, dynamic>.from(item)),
          )
          .toList(),
    );
  }
}

class ItemOrdemLavanderia {
  final String nomeCategoria;
  final String nomeServico;
  final int quantidade;
  final double valorUnitario;
  final double subtotal;
  final String observacao;

  const ItemOrdemLavanderia({
    required this.nomeCategoria,
    required this.nomeServico,
    required this.quantidade,
    required this.valorUnitario,
    required this.subtotal,
    required this.observacao,
  });

  factory ItemOrdemLavanderia.fromMap(Map<String, dynamic> map) {
    return ItemOrdemLavanderia(
      nomeCategoria: map['nome_categoria'] ?? '',
      nomeServico: map['nome_servico'] ?? '',
      quantidade: map['quantidade'] ?? 0,
      valorUnitario: (map['valor_unitario'] as num?)?.toDouble() ?? 0.0,
      subtotal: (map['subtotal'] as num?)?.toDouble() ?? 0.0,
      observacao: map['observacao'] ?? '',
    );
  }
}
