// Representa uma reserva aberta usada nos fluxos de pedido, bebida e conta.
// Tambem carrega dados relacionados de hospede, quarto e ContaConsumo.
class Reserva {
  // Identificadores das tabelas relacionadas.
  final String idReserva;
  final String idHospede;
  final String idQuarto;
  final String idConta;

  // Dados exibidos nos dropdowns e cards.
  final String nomeHospede;
  final String numeroQuarto;
  final String statusReserva;
  final String statusConta;

  Reserva({
    required this.idReserva,
    required this.idHospede,
    required this.idQuarto,
    required this.idConta,
    required this.nomeHospede,
    required this.numeroQuarto,
    required this.statusReserva,
    required this.statusConta,
  });

  // Converte a resposta da API em Reserva, incluindo relacionamentos.
  factory Reserva.fromMap(Map<String, dynamic> map) {
    // Dados aninhados vindos do relacionamento hospede:id_hospede.
    final hospede =
        map['hospede'] as Map<String, dynamic>? ?? <String, dynamic>{};

    // Dados aninhados vindos do relacionamento quarto:id_quarto.
    final quarto =
        map['quarto'] as Map<String, dynamic>? ?? <String, dynamic>{};

    // Conta vinculada a reserva, usada para lancar consumos e fechar conta.
    final conta =
        map['conta_consumo'] as Map<String, dynamic>? ?? <String, dynamic>{};

    return Reserva(
      idReserva: (map['id_reserva'] ?? '').toString(),
      idHospede: (map['id_hospede'] ?? '').toString(),
      idQuarto: (map['id_quarto'] ?? '').toString(),
      idConta: (map['id_conta'] ?? conta['id_conta'] ?? '').toString(),
      nomeHospede: map['nome_hospede'] ?? hospede['nome_hospede'] ?? '',
      numeroQuarto: (map['numero_quarto'] ?? quarto['numero_quarto'] ?? '')
          .toString(),
      statusReserva: map['status_reserva'] ?? '',
      statusConta: map['status_conta'] ?? conta['status_conta'] ?? '',
    );
  }

  // Texto pronto para aparecer nos dropdowns das telas.
  String get descricaoDropdown {
    return 'Quarto $numeroQuarto - $nomeHospede ($statusReserva)';
  }

  // Regra usada para filtrar reservas que ainda podem receber consumo.
  bool get possuiContaAberta {
    return idConta.isNotEmpty && statusConta == 'Aberta';
  }
}
