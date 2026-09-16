import 'package:bravo_restaurante/widgets/cores_app.dart';
import 'package:flutter/material.dart';

// Botao principal padrao para acoes de confirmacao ou salvamento.
class BotaoAcaoPrincipal extends StatelessWidget {
  final String label;
  final IconData icon;
  final VoidCallback? onPressed;
  final Color backgroundColor;
  final double height;
  final double borderRadius;

  const BotaoAcaoPrincipal({
    super.key,
    required this.label,
    required this.icon,
    required this.onPressed,
    this.backgroundColor = CoresApp.verdeEscuro,
    this.height = 58,
    this.borderRadius = 8,
  });

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: double.infinity,
      height: height,
      child: ElevatedButton.icon(
        onPressed: onPressed,
        icon: Icon(icon, color: Colors.white, size: 24),
        label: Text(
          label,
          style: const TextStyle(
            fontSize: 16,
            color: Colors.white,
            fontWeight: FontWeight.bold,
          ),
        ),
        style: ElevatedButton.styleFrom(
          backgroundColor: backgroundColor,
          disabledBackgroundColor: Colors.grey.shade400,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(borderRadius),
          ),
        ),
      ),
    );
  }
}
