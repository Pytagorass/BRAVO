import 'package:bravo_restaurante/widgets/cores_app.dart';
import 'package:flutter/material.dart';

// Rotulo padrao usado antes dos campos de formulario do aplicativo.
class RotuloFormulario extends StatelessWidget {
  final String texto;

  const RotuloFormulario(this.texto, {super.key});

  @override
  Widget build(BuildContext context) {
    return Text(
      texto,
      style: const TextStyle(
        fontWeight: FontWeight.w600,
        color: CoresApp.cinzaEscuro,
      ),
    );
  }
}
