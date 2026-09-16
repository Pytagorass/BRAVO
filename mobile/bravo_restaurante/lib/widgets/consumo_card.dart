import 'package:bravo_restaurante/widgets/cores_app.dart';
import 'package:flutter/material.dart';

// Card padrao para exibir um consumo com data, itens, observacao e total.
class ConsumoCard extends StatelessWidget {
  final String titulo;
  final String data;
  final List<String> itens;
  final double total;
  final String? observacao;
  final String totalLabel;

  const ConsumoCard({
    super.key,
    this.titulo = 'Pedido',
    required this.data,
    required this.itens,
    required this.total,
    this.observacao,
    this.totalLabel = 'Total:',
  });

  @override
  Widget build(BuildContext context) {
    final observacaoTratada = observacao?.trim() ?? '';

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(titulo, style: const TextStyle(fontWeight: FontWeight.w600)),
            Text('Data: $data'),
            if (observacaoTratada.isNotEmpty) ...[
              const SizedBox(height: 4),
              Text('Observacao: $observacaoTratada'),
            ],
            const SizedBox(height: 4),
            ...itens.map((item) => Text(item)),
            const SizedBox(height: 6),
            Text(
              '$totalLabel R\$ ${total.toStringAsFixed(2)}',
              style: const TextStyle(
                fontWeight: FontWeight.bold,
                color: CoresApp.verdeEscuro,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
