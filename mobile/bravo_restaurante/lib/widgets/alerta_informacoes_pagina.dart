import 'package:bravo_restaurante/widgets/cores_app.dart';
import 'package:flutter/material.dart';

// Widget reutilizavel para mostrar mensagens informativas no topo das telas.
class AlertaInformacoesPagina extends StatelessWidget {
  // Texto exibido dentro do alerta.
  final String message;

  // Icone opcional para adaptar o alerta ao contexto da tela.
  final IconData icon;

  const AlertaInformacoesPagina({
    super.key,
    required this.message,
    this.icon = Icons.info_outline,
  });

  @override
  Widget build(BuildContext context) {
    // Container com fundo destacado e largura total para chamar a atencao.
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFFEAF3FF),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.blue.shade100),
      ),
      child: Row(
        children: [
          // Icone visual que reforca o tipo da mensagem.
          Icon(icon, color: Colors.blue),
          const SizedBox(width: 8),
          // Expanded evita que textos longos estourem a largura da tela.
          Expanded(
            child: Text(
              message,
              style: const TextStyle(
                color: CoresApp.cinzaEscuro,
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
