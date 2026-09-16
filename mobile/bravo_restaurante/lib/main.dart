import 'package:bravo_restaurante/mvvm/conta_consumo_viewmodel.dart';
import 'package:bravo_restaurante/mvvm/bebida_viewmodel.dart';
import 'package:bravo_restaurante/mvvm/pedido_viewmodel.dart';
import 'package:bravo_restaurante/mvvm/produto_viewmodel.dart';
import 'package:bravo_restaurante/mvvm/reserva_viewmodel.dart';
import 'package:bravo_restaurante/mvvm/usuario_viewmodel.dart';
import 'package:bravo_restaurante/pages/login/login_view.dart';
import 'package:bravo_restaurante/widgets/cores_app.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

Future<void> main() async {
  // Garante que o Flutter esteja pronto antes de inicializar servicos externos.
  WidgetsFlutterBinding.ensureInitialized();

  // Registra os ViewModels que serao usados pelas telas com Provider.
  runApp(
    MultiProvider(
      providers: [
        // Guarda dados do usuario logado e regras de autenticacao.
        ChangeNotifierProvider(create: (_) => UsuarioViewModel()),
        // Carrega produtos usados em lancamentos da lojinha e de bebida.
        ChangeNotifierProvider(create: (_) => ProdutoViewModel()),
        // Carrega reservas abertas para selecionar quarto/hospede.
        ChangeNotifierProvider(create: (_) => ReservaViewModel()),
        // Controla criacao e envio dos lancamentos da lojinha.
        ChangeNotifierProvider(create: (_) => PedidoViewModel()),
        // Consulta o resumo de consumo da conta do hospede.
        ChangeNotifierProvider(create: (_) => ContaConsumoViewModel()),
        // Registra bebidas diretamente na ContaConsumo.
        ChangeNotifierProvider(create: (_) => BebidaViewModel()),
      ],
      child: const BravoApp(),
    ),
  );
}

// Widget raiz do aplicativo: define tema, titulo e tela inicial.
class BravoApp extends StatelessWidget {
  const BravoApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'BRAVO Consumo',
      debugShowCheckedModeBanner: false,

      theme: ThemeData(
        // Cor principal usada nas barras, botoes e componentes do app.
        primaryColor: CoresApp.verdeEscuro,

        scaffoldBackgroundColor: Colors.white,

        colorScheme: ColorScheme.fromSeed(seedColor: CoresApp.verdeEscuro),
      ),

      // A primeira tela exibida quando o aplicativo abre.
      home: const LoginView(),
    );
  }
}
