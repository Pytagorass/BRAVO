import 'package:bravo_restaurante/models/reserva.dart';
import 'package:bravo_restaurante/mvvm/reserva_viewmodel.dart';
import 'package:bravo_restaurante/widgets/rotulo_formulario.dart';
import 'package:flutter/material.dart';

// Dropdown padrao para selecionar reservas abertas em formularios e consultas.
class ReservaDropdown extends StatelessWidget {
  final ReservaViewModel reservaVM;
  final Reserva? reservaSelecionada;
  final ValueChanged<Reserva?> onChanged;
  final FormFieldValidator<Reserva>? validator;
  final String hintText;
  final String emptyMessage;
  final String? label;
  final bool mostrarLoading;
  final Widget Function(String mensagem)? mensagemBuilder;

  const ReservaDropdown({
    super.key,
    required this.reservaVM,
    required this.reservaSelecionada,
    required this.onChanged,
    this.validator,
    this.hintText = 'Selecione a reserva',
    this.emptyMessage = 'Nenhuma reserva aberta encontrada.',
    this.label,
    this.mostrarLoading = false,
    this.mensagemBuilder,
  });

  @override
  Widget build(BuildContext context) {
    if (mostrarLoading && reservaVM.isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (reservaVM.mensagemErro != null) {
      return _buildMensagem(reservaVM.mensagemErro!);
    }

    if (reservaVM.reservas.isEmpty) {
      return _buildMensagem(emptyMessage);
    }

    final dropdown = DropdownButtonFormField<Reserva>(
      initialValue: reservaSelecionada,
      decoration: const InputDecoration(
        border: OutlineInputBorder(),
        contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 14),
      ),
      hint: Text(hintText),
      items: reservaVM.reservas.map((reserva) {
        return DropdownMenuItem<Reserva>(
          value: reserva,
          child: Text(reserva.descricaoDropdown),
        );
      }).toList(),
      onChanged: onChanged,
      validator: validator,
    );

    if (label == null) return dropdown;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [RotuloFormulario(label!), const SizedBox(height: 6), dropdown],
    );
  }

  Widget _buildMensagem(String mensagem) {
    if (mensagemBuilder != null) {
      return mensagemBuilder!(mensagem);
    }

    return Text(mensagem, style: const TextStyle(color: Colors.red));
  }
}
