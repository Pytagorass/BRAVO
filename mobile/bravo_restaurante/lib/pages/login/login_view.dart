import 'dart:async';

import 'package:bravo_restaurante/mvvm/usuario_viewmodel.dart';
import 'package:bravo_restaurante/pages/home/home_view.dart';
import 'package:bravo_restaurante/services/mobile_access_control.dart';
import 'package:bravo_restaurante/widgets/cores_app.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

class LoginView extends StatefulWidget {
  const LoginView({super.key});

  @override
  State<LoginView> createState() => _LoginViewState();
}

class _LoginViewState extends State<LoginView> {
  // Chave do formulario usada para validar e-mail e senha juntos.
  final _formKey = GlobalKey<FormState>();

  // Controllers leem o texto digitado nos campos de login.
  final _emailController = TextEditingController();
  final _senhaController = TextEditingController();

  // Controla se a senha aparece escondida ou visivel.
  bool _obscurePassword = true;

  // Bloqueia o botao e exibe loading durante a tentativa de login.
  bool _isLoading = false;

  @override
  void dispose() {
    // Libera os controllers quando a tela sair da memória.
    _emailController.dispose();
    _senhaController.dispose();
    super.dispose();
  }

  Future<void> _login() async {
    // Interrompe o fluxo se algum campo obrigatório estiver inválido.
    if (!_formKey.currentState!.validate()) return;

    // Fecha o teclado e bloqueia o botão enquanto a consulta ao banco acontece.
    FocusScope.of(context).unfocus();
    setState(() => _isLoading = true);

    final usuarioVM = Provider.of<UsuarioViewModel>(context, listen: false);
    final email = _emailController.text.trim();
    final senha = _senhaController.text.trim();

    try {
      // Evita deixar a tela presa em "Entrando..." se a API nao responder.
      final sucesso = await usuarioVM
          .login(email: email, senha: senha)
          .timeout(const Duration(seconds: 12));

      if (!mounted) return;

      if (sucesso) {
        if (!MobileAccessControl.hasAnyMobileAccess(usuarioVM.usuarioLogado)) {
          usuarioVM.logout();
          _mostrarErro('Usuario sem permissao para acessar o app mobile.');
          return;
        }

        // Login validado: remove a tela de login da pilha e abre a Home.
        Navigator.of(
          context,
        ).pushReplacement(MaterialPageRoute(builder: (_) => const HomeView()));
        return;
      }

      debugPrint('Login falhou: ${usuarioVM.mensagemErro}');
      _mostrarErro(usuarioVM.mensagemErro ?? 'E-mail ou senha incorretos.');
    } on TimeoutException {
      if (!mounted) return;

      // Mensagem específica para falha de comunicação, diferente de senha errada.
      debugPrint('Login falhou: tempo limite na comunicacao com a API.');
      _mostrarErro('Tempo limite ao conectar com a API.');
    } catch (e) {
      if (!mounted) return;

      debugPrint('Login falhou: $e');
      _mostrarErro('Erro ao realizar login. Tente novamente.');
    } finally {
      // Garante que o botão volte ao estado normal em sucesso, erro ou timeout.
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  void _mostrarErro(String mensagem) {
    // Centraliza a exibição de erros.
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(mensagem, textAlign: TextAlign.center),
        backgroundColor: Colors.redAccent,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    // Tela de entrada com logo, formulario e botao de autenticacao.
    return Scaffold(
      backgroundColor: const Color(0xFFF4F6F3),
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Column(
            children: [
              Image.asset('assets/LogoBravo.png', height: 250, width: 250),

              const SizedBox(height: 16),

              const Text(
                'BRAVO Consumo',
                style: TextStyle(
                  fontSize: 24,
                  fontWeight: FontWeight.bold,
                  color: CoresApp.verdeEscuro,
                ),
              ),

              const SizedBox(height: 4),

              const Text(
                'Controle de bebidas, lojinha e lavanderia do barco-hotel',
                textAlign: TextAlign.center,
                style: TextStyle(color: CoresApp.cinzaEscuro),
              ),

              const SizedBox(height: 32),

              // Card central que agrupa os campos obrigatorios do login.
              Card(
                elevation: 6,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(16),
                ),
                child: Padding(
                  padding: const EdgeInsets.all(24),
                  child: Form(
                    key: _formKey,
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        // Campo de e-mail validado antes de chamar o ViewModel.
                        TextFormField(
                          controller: _emailController,
                          decoration: const InputDecoration(
                            labelText: 'E-mail',
                            prefixIcon: Icon(Icons.email_outlined),
                            border: OutlineInputBorder(),
                          ),
                          keyboardType: TextInputType.emailAddress,
                          validator: (value) {
                            if (value == null || value.trim().isEmpty) {
                              return 'Digite seu e-mail';
                            }

                            if (!value.contains('@')) {
                              return 'E-mail inválido';
                            }

                            return null;
                          },
                        ),

                        const SizedBox(height: 16),

                        // Campo de senha com botao para alternar visibilidade.
                        TextFormField(
                          controller: _senhaController,
                          obscureText: _obscurePassword,
                          decoration: InputDecoration(
                            labelText: 'Senha',
                            prefixIcon: const Icon(Icons.lock_outline),
                            border: const OutlineInputBorder(),
                            suffixIcon: IconButton(
                              icon: Icon(
                                _obscurePassword
                                    ? Icons.visibility
                                    : Icons.visibility_off,
                              ),
                              onPressed: () {
                                setState(() {
                                  // Alterna entre mostrar e esconder a senha digitada.
                                  _obscurePassword = !_obscurePassword;
                                });
                              },
                            ),
                          ),
                          validator: (value) {
                            if (value == null || value.trim().isEmpty) {
                              return 'Digite sua senha';
                            }

                            return null;
                          },
                        ),

                        const SizedBox(height: 24),

                        // Botao principal: chama login ou mostra progresso.
                        SizedBox(
                          width: double.infinity,
                          child: ElevatedButton.icon(
                            onPressed: _isLoading ? null : _login,
                            icon: _isLoading
                                ? const SizedBox(
                                    width: 16,
                                    height: 16,
                                    child: CircularProgressIndicator(
                                      strokeWidth: 2,
                                      color: Colors.white,
                                    ),
                                  )
                                : const Icon(
                                    Icons.login_rounded,
                                    color: Colors.white,
                                  ),
                            label: Text(
                              _isLoading ? 'Entrando...' : 'Entrar',
                              style: const TextStyle(
                                fontSize: 16,
                                color: Colors.white,
                              ),
                            ),
                            style: ElevatedButton.styleFrom(
                              backgroundColor: CoresApp.verdeEscuro,
                              padding: const EdgeInsets.symmetric(vertical: 14),
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(12),
                              ),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),

              const SizedBox(height: 16),

              Text(
                'BRAVO • Barco-Hotel',
                style: TextStyle(
                  color: CoresApp.verdeMedio,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
