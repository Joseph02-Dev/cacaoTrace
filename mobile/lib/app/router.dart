import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

/// Squelette de navigation (socle MOB-1b). Les écrans réels — Bienvenue,
/// Connexion identifiant, Connexion PIN, Accueil, Nouvel achat, Achats,
/// Détail, Synchronisation, Réglages — sont livrés avec MOB-2 à MOB-5
/// (design-cacaotrack-gn.md v0.2). Ici : uniquement les chemins et des
/// pages vides, pour que le socle compile et navigue.
abstract final class AppRoutes {
  static const welcome = '/welcome';
  static const login = '/login';
  static const pin = '/pin';
  static const home = '/home';
  static const newPurchase = '/purchases/new';
  static const purchases = '/purchases';
  static const purchaseDetail = '/purchases/:id';
  static const sync = '/sync';
  static const settings = '/settings';
}

GoRouter buildRouter() {
  return GoRouter(
    initialLocation: AppRoutes.welcome,
    routes: [
      GoRoute(
        path: AppRoutes.welcome,
        builder: (context, state) => const _PlaceholderScreen(title: 'Bienvenue'),
      ),
      GoRoute(
        path: AppRoutes.login,
        builder: (context, state) => const _PlaceholderScreen(title: 'Connexion'),
      ),
      GoRoute(
        path: AppRoutes.pin,
        builder: (context, state) => const _PlaceholderScreen(title: 'PIN'),
      ),
      GoRoute(
        path: AppRoutes.home,
        builder: (context, state) => const _PlaceholderScreen(title: 'Accueil'),
      ),
      GoRoute(
        path: AppRoutes.newPurchase,
        builder: (context, state) => const _PlaceholderScreen(title: 'Nouvel achat'),
      ),
      GoRoute(
        path: AppRoutes.purchases,
        builder: (context, state) => const _PlaceholderScreen(title: 'Achats'),
      ),
      GoRoute(
        path: AppRoutes.purchaseDetail,
        builder: (context, state) => _PlaceholderScreen(
          title: 'Détail achat ${state.pathParameters['id']}',
        ),
      ),
      GoRoute(
        path: AppRoutes.sync,
        builder: (context, state) => const _PlaceholderScreen(title: 'Synchronisation'),
      ),
      GoRoute(
        path: AppRoutes.settings,
        builder: (context, state) => const _PlaceholderScreen(title: 'Réglages'),
      ),
    ],
  );
}

class _PlaceholderScreen extends StatelessWidget {
  const _PlaceholderScreen({required this.title});

  final String title;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(title)),
      body: Center(child: Text('$title — à venir')),
    );
  }
}
