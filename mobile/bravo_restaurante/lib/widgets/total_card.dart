import 'package:bravo_restaurante/widgets/cores_app.dart';
import 'package:flutter/material.dart';

// Card padrao para destacar valores totais antes ou depois de uma operacao.
class TotalCard extends StatelessWidget {
  final String titulo;
  final double valor;
  final Color backgroundColor;
  final double valorFontSize;

  const TotalCard({
    super.key,
    required this.titulo,
    required this.valor,
    this.backgroundColor = CoresApp.verdeMedio,
    this.valorFontSize = 24,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: backgroundColor,
        borderRadius: BorderRadius.circular(10),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            titulo,
            style: const TextStyle(
              color: Colors.white,
              fontWeight: FontWeight.w600,
            ),
          ),
          Text(
            'R\$ ${valor.toStringAsFixed(2)}',
            style: TextStyle(
              color: Colors.white,
              fontSize: valorFontSize,
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      ),
    );
  }
}
