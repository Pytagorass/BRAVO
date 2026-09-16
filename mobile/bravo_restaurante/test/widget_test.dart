import 'package:bravo_restaurante/mvvm/usuario_viewmodel.dart';
import 'package:bravo_restaurante/pages/home/home_view.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';

void main() {
  testWidgets('HomeView renders the consumption shortcuts', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      ChangeNotifierProvider(
        create: (_) => UsuarioViewModel(),
        child: const MaterialApp(home: HomeView()),
      ),
    );

    expect(find.text('BRAVO Consumo'), findsOneWidget);
    expect(find.text('Bebidas'), findsWidgets);
    expect(find.text('Lojinha'), findsWidgets);
  });
}
