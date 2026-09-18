import 'package:bravo_restaurante/models/usuario.dart';
import 'package:bravo_restaurante/mvvm/usuario_viewmodel.dart';
import 'package:bravo_restaurante/pages/bebida/lancar_bebida_view.dart';
import 'package:bravo_restaurante/pages/conta/conta_hospede_view.dart';
import 'package:bravo_restaurante/pages/conta/fechar_conta_view.dart';
import 'package:bravo_restaurante/pages/lavanderia/lavanderia_view.dart';
import 'package:bravo_restaurante/pages/login/login_view.dart';
import 'package:bravo_restaurante/pages/pedido/registrar_pedido_view.dart';
import 'package:bravo_restaurante/services/mobile_access_control.dart';
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

  bool _usuarioPode(bool Function(Usuario? usuario) regra) {
    final usuario = context.read<UsuarioViewModel>().usuarioLogado;
    if (regra(usuario)) {
      return true;
    }

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: const Text('Usuario sem permissao para acessar este recurso.'),
        backgroundColor: Colors.redAccent,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      ),
    );
    return false;
  }

  void _abrirLojinha() {
    if (!_usuarioPode(MobileAccessControl.canLancamentoConsumo)) return;

    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) =>
            const RegistrarPedidoView(origem: 'Lojinha', titulo: 'Lojinha'),
      ),
    );
  }

  void _abrirLavanderia() {
    if (!_usuarioPode(MobileAccessControl.canLavanderia)) return;

    Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => const LavanderiaView()),
    );
  }

  void _abrirLancarBebida() {
    if (!_usuarioPode(MobileAccessControl.canLancamentoConsumo)) return;

    Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => const LancarBebidaView()),
    );
  }

  void _abrirContaHospede() {
    if (!_usuarioPode(MobileAccessControl.canVerConta)) return;

    Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => const ContaHospedeView()),
    );
  }

  void _abrirFecharConta() {
    if (!_usuarioPode(MobileAccessControl.canFecharConta)) return;

    Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => const FecharContaView()),
    );
  }

  void _fecharDrawerEAbrir(VoidCallback abrirTela) {
    Navigator.pop(context);
    abrirTela();
  }

  List<_HomeAction> _buildQuickActions(Usuario? usuario) {
    return [
      if (MobileAccessControl.canLancamentoConsumo(usuario))
        _HomeAction(
          label: 'Bebidas',
          icon: Icons.local_bar,
          onTap: _abrirLancarBebida,
        ),
      if (MobileAccessControl.canLancamentoConsumo(usuario))
        _HomeAction(
          label: 'Lojinha',
          icon: Icons.storefront,
          onTap: _abrirLojinha,
        ),
      if (MobileAccessControl.canLavanderia(usuario))
        _HomeAction(
          label: 'Lavanderia',
          icon: Icons.local_laundry_service,
          onTap: _abrirLavanderia,
        ),
      if (MobileAccessControl.canVerConta(usuario))
        _HomeAction(
          label: 'Conta',
          icon: Icons.account_balance_wallet,
          onTap: _abrirContaHospede,
        ),
      if (MobileAccessControl.canFecharConta(usuario))
        _HomeAction(
          label: 'Fechar Conta',
          icon: Icons.attach_money,
          onTap: _abrirFecharConta,
        ),
    ];
  }

  List<_HomeAction> _buildBottomActions(Usuario? usuario) {
    return [
      const _HomeAction(label: 'Home', icon: Icons.home_outlined),
      if (MobileAccessControl.canLancamentoConsumo(usuario))
        _HomeAction(
          label: 'Bebidas',
          icon: Icons.local_bar,
          onTap: _abrirLancarBebida,
        ),
      if (MobileAccessControl.canLavanderia(usuario))
        _HomeAction(
          label: 'Lavanderia',
          icon: Icons.local_laundry_service,
          onTap: _abrirLavanderia,
        ),
      if (MobileAccessControl.canVerConta(usuario))
        _HomeAction(
          label: 'Conta',
          icon: Icons.account_balance_wallet,
          onTap: _abrirContaHospede,
        ),
      if (MobileAccessControl.canFecharConta(usuario))
        _HomeAction(
          label: 'Fechar',
          icon: Icons.attach_money,
          onTap: _abrirFecharConta,
        ),
    ];
  }

  @override
  Widget build(BuildContext context) {
    final usuario = context.watch<UsuarioViewModel>().usuarioLogado;
    final quickActions = _buildQuickActions(usuario);
    final bottomActions = _buildBottomActions(usuario);
    final selectedIndex = _selectedIndex < bottomActions.length
        ? _selectedIndex
        : 0;

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
      drawer: _buildDrawer(usuario),
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
              actions: quickActions,
            ),
          ],
        ),
      ),
      bottomNavigationBar: bottomActions.length >= 2
          ? BottomNavigationBar(
              currentIndex: selectedIndex,
              type: BottomNavigationBarType.fixed,
              selectedItemColor: CoresApp.verdeEscuro,
              unselectedItemColor: CoresApp.cinzaEscuro.withValues(alpha: 0.6),
              iconSize: 26,
              selectedFontSize: 13,
              unselectedFontSize: 12,
              showUnselectedLabels: true,
              onTap: (index) {
                if (index == 0) {
                  setState(() => _selectedIndex = 0);
                  return;
                }

                setState(() => _selectedIndex = 0);
                bottomActions[index].onTap?.call();
              },
              items: bottomActions
                  .map(
                    (action) => BottomNavigationBarItem(
                      icon: Icon(action.icon),
                      label: action.label,
                    ),
                  )
                  .toList(),
            )
          : null,
    );
  }

  Drawer _buildDrawer(Usuario? usuario) {
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
          if (MobileAccessControl.canLancamentoConsumo(usuario))
            ListTile(
              leading: const Icon(Icons.local_bar),
              title: const Text('Bebidas'),
              onTap: () => _fecharDrawerEAbrir(_abrirLancarBebida),
            ),
          if (MobileAccessControl.canLancamentoConsumo(usuario))
            ListTile(
              leading: const Icon(Icons.storefront),
              title: const Text('Lojinha'),
              onTap: () => _fecharDrawerEAbrir(_abrirLojinha),
            ),
          if (MobileAccessControl.canLavanderia(usuario))
            ListTile(
              leading: const Icon(Icons.local_laundry_service),
              title: const Text('Lavanderia'),
              onTap: () => _fecharDrawerEAbrir(_abrirLavanderia),
            ),
          if (MobileAccessControl.canVerConta(usuario))
            ListTile(
              leading: const Icon(Icons.account_balance_wallet),
              title: const Text('Conta do Hospede'),
              onTap: () => _fecharDrawerEAbrir(_abrirContaHospede),
            ),
          if (MobileAccessControl.canFecharConta(usuario))
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

class _HomeAction {
  final String label;
  final IconData icon;
  final VoidCallback? onTap;

  const _HomeAction({
    required this.label,
    required this.icon,
    this.onTap,
  });
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
                'Controle de bebidas, lojinha e lavanderia do barco-hotel',
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
  final List<_HomeAction> actions;

  const _AcessosRapidosCard({
    required this.actions,
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
            if (actions.isEmpty)
              const Text(
                'Este perfil nao possui funcionalidades liberadas no app mobile.',
                style: TextStyle(color: CoresApp.cinzaEscuro),
              )
            else
              LayoutBuilder(
                builder: (context, constraints) {
                  final colunas = actions.length == 1 ? 1 : (isTablet ? 3 : 2);
                  final largura = (constraints.maxWidth -
                          (espacamento * (colunas - 1))) /
                      colunas;

                  return Wrap(
                    spacing: espacamento,
                    runSpacing: espacamento,
                    children: actions
                        .map(
                          (action) => SizedBox(
                            width: largura,
                            child: _QuickButton(
                              label: action.label,
                              icon: action.icon,
                              onTap: action.onTap!,
                            ),
                          ),
                        )
                        .toList(),
                  );
                },
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
