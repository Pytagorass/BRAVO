import 'package:bravo_restaurante/mvvm/usuario_viewmodel.dart';
import 'package:bravo_restaurante/pages/bebida/lancar_bebida_view.dart';
import 'package:bravo_restaurante/pages/conta/conta_hospede_view.dart';
import 'package:bravo_restaurante/pages/conta/fechar_conta_view.dart';
import 'package:bravo_restaurante/pages/login/login_view.dart';
import 'package:bravo_restaurante/pages/pedido/registrar_pedido_view.dart';
import 'package:bravo_restaurante/widgets/cores_app.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

class HomeView extends StatefulWidget {
  const HomeView({super.key});

  @override
  State<HomeView> createState() => _HomeViewState();
}

class _HomeViewState extends State<HomeView> {
  int _selectedIndex = 0;

  void _logout() {
    context.read<UsuarioViewModel>().logout();
    Navigator.of(context).pushAndRemoveUntil(
      MaterialPageRoute(builder: (_) => const LoginView()),
      (route) => false,
    );
  }

  void _abrirLojinha() {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) =>
            const RegistrarPedidoView(origem: 'Lojinha', titulo: 'Lojinha'),
      ),
    );
  }

  void _abrirLancarBebida() {
    Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => const LancarBebidaView()),
    );
  }

  void _abrirContaHospede() {
    Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => const ContaHospedeView()),
    );
  }

  void _abrirFecharConta() {
    Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => const FecharContaView()),
    );
  }

  void _fecharDrawerEAbrir(VoidCallback abrirTela) {
    Navigator.pop(context);
    abrirTela();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('BRAVO Consumo'),
        backgroundColor: CoresApp.verdeEscuro,
        foregroundColor: Colors.white,
        actions: [
          IconButton(
            icon: const Icon(Icons.logout),
            tooltip: 'Sair',
            onPressed: _logout,
          ),
        ],
      ),
      drawer: _buildDrawer(),
      body: RefreshIndicator(
        onRefresh: () async {
          await Future.delayed(const Duration(milliseconds: 500));
        },
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            _ResumoCard(),
            const SizedBox(height: 16),
            _AcessosRapidosCard(
              abrirLancarBebida: _abrirLancarBebida,
              abrirLojinha: _abrirLojinha,
              abrirContaHospede: _abrirContaHospede,
              abrirFecharConta: _abrirFecharConta,
            ),
          ],
        ),
      ),
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _selectedIndex,
        selectedItemColor: CoresApp.verdeEscuro,
        unselectedItemColor: CoresApp.cinzaEscuro.withValues(alpha: 0.6),
        iconSize: 26,
        selectedFontSize: 13,
        unselectedFontSize: 12,
        showUnselectedLabels: true,
        onTap: (index) {
          setState(() => _selectedIndex = index);

          if (index == 1) {
            _abrirLancarBebida();
          } else if (index == 2) {
            _abrirContaHospede();
          } else if (index == 3) {
            _abrirFecharConta();
          }
        },
        items: const [
          BottomNavigationBarItem(
            icon: Icon(Icons.home_outlined),
            label: 'Home',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.local_bar),
            label: 'Bebidas',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.account_balance_wallet),
            label: 'Conta',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.attach_money),
            label: 'Fechar',
          ),
        ],
      ),
    );
  }

  Drawer _buildDrawer() {
    final usuario = context.watch<UsuarioViewModel>().usuarioLogado;

    return Drawer(
      child: Column(
        children: [
          UserAccountsDrawerHeader(
            decoration: const BoxDecoration(color: CoresApp.verdeEscuro),
            accountName: Text(
              usuario?.nomeUsuario.isNotEmpty == true
                  ? usuario!.nomeUsuario
                  : 'Usuario',
            ),
            accountEmail: Text(usuario?.emailUsuario ?? ''),
            currentAccountPicture: const CircleAvatar(
              backgroundColor: Colors.white,
              child: Icon(Icons.person, color: CoresApp.verdeEscuro),
            ),
          ),
          ListTile(
            leading: const Icon(Icons.local_bar),
            title: const Text('Bebidas'),
            onTap: () => _fecharDrawerEAbrir(_abrirLancarBebida),
          ),
          ListTile(
            leading: const Icon(Icons.storefront),
            title: const Text('Lojinha'),
            onTap: () => _fecharDrawerEAbrir(_abrirLojinha),
          ),
          ListTile(
            leading: const Icon(Icons.account_balance_wallet),
            title: const Text('Conta do Hospede'),
            onTap: () => _fecharDrawerEAbrir(_abrirContaHospede),
          ),
          ListTile(
            leading: const Icon(Icons.attach_money),
            title: const Text('Fechar Conta'),
            onTap: () => _fecharDrawerEAbrir(_abrirFecharConta),
          ),
          const Spacer(),
          ListTile(
            leading: const Icon(Icons.logout, color: Colors.red),
            title: const Text('Sair', style: TextStyle(color: Colors.red)),
            onTap: _logout,
          ),
        ],
      ),
    );
  }
}

class _ResumoCard extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
      child: const Padding(
        padding: EdgeInsets.all(16),
        child: Row(
          children: [
            CircleAvatar(
              backgroundColor: CoresApp.verdeMedio,
              child: Icon(Icons.point_of_sale, color: Colors.white),
            ),
            SizedBox(width: 12),
            Expanded(
              child: Text(
                'Controle de bebidas e lojinha do barco-hotel',
                style: TextStyle(
                  fontWeight: FontWeight.w600,
                  color: CoresApp.verdeEscuro,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _AcessosRapidosCard extends StatelessWidget {
  final VoidCallback abrirLancarBebida;
  final VoidCallback abrirLojinha;
  final VoidCallback abrirContaHospede;
  final VoidCallback abrirFecharConta;

  const _AcessosRapidosCard({
    required this.abrirLancarBebida,
    required this.abrirLojinha,
    required this.abrirContaHospede,
    required this.abrirFecharConta,
  });

  @override
  Widget build(BuildContext context) {
    final isTablet = MediaQuery.sizeOf(context).shortestSide >= 600;
    final paddingCard = isTablet ? 22.0 : 16.0;
    final espacamento = isTablet ? 16.0 : 12.0;

    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
      child: Padding(
        padding: EdgeInsets.all(paddingCard),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Acessos rapidos',
              style: TextStyle(
                fontSize: isTablet ? 18 : 16,
                fontWeight: FontWeight.w600,
              ),
            ),
            SizedBox(height: espacamento),
            Row(
              children: [
                Expanded(
                  child: _QuickButton(
                    label: 'Bebidas',
                    icon: Icons.local_bar,
                    onTap: abrirLancarBebida,
                  ),
                ),
                SizedBox(width: espacamento),
                Expanded(
                  child: _QuickButton(
                    label: 'Lojinha',
                    icon: Icons.storefront,
                    onTap: abrirLojinha,
                  ),
                ),
              ],
            ),
            SizedBox(height: espacamento),
            Row(
              children: [
                Expanded(
                  child: _QuickButton(
                    label: 'Conta',
                    icon: Icons.account_balance_wallet,
                    onTap: abrirContaHospede,
                  ),
                ),
                SizedBox(width: espacamento),
                Expanded(
                  child: _QuickButton(
                    label: 'Fechar Conta',
                    icon: Icons.attach_money,
                    onTap: abrirFecharConta,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _QuickButton extends StatelessWidget {
  final String label;
  final IconData icon;
  final VoidCallback onTap;

  const _QuickButton({
    required this.label,
    required this.icon,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final isTablet = MediaQuery.sizeOf(context).shortestSide >= 600;

    return OutlinedButton.icon(
      onPressed: onTap,
      icon: Icon(icon, color: CoresApp.verdeMedio, size: isTablet ? 24 : 20),
      label: Text(
        label,
        textAlign: TextAlign.center,
        style: TextStyle(
          fontSize: isTablet ? 15 : 13,
          color: CoresApp.verdeEscuro,
          fontWeight: FontWeight.w600,
        ),
      ),
      style: OutlinedButton.styleFrom(
        minimumSize: Size.fromHeight(isTablet ? 58 : 48),
        side: BorderSide(color: CoresApp.verdeMedio.withValues(alpha: 0.6)),
        padding: EdgeInsets.symmetric(
          vertical: isTablet ? 18 : 14,
          horizontal: isTablet ? 16 : 8,
        ),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      ),
    );
  }
}
