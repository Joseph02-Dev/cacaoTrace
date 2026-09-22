import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/local/database.dart';
import '../data/network/api_client.dart';
import '../data/secure/database_key_provider.dart';
import '../data/secure/secure_storage.dart';
import 'router.dart';

/// URL de base de l'API (inclut déjà `/api/v1/`, P2 architecture) —
/// surchargée en build via `--dart-define=API_BASE_URL=https://.../api/v1/`.
/// La valeur par défaut est un espace réservé : elle doit être fixée avec
/// le client avant tout build de test terrain.
const apiBaseUrl = String.fromEnvironment(
  'API_BASE_URL',
  defaultValue: 'https://CHANGE_ME.example/api/v1/',
);

final secureStorageProvider = Provider<AppSecureStorage>((ref) {
  return AppSecureStorage();
});

final databaseKeyProviderProvider = Provider<DatabaseKeyProvider>((ref) {
  return DatabaseKeyProvider(ref.watch(secureStorageProvider).raw);
});

/// Base Drift chiffrée (P1). Asynchrone : la clé doit être lue/générée dans
/// le stockage sécurisé avant l'ouverture du fichier SQLite.
final databaseProvider = FutureProvider<AppDatabase>((ref) async {
  final key = await ref.watch(databaseKeyProviderProvider).getOrCreateKey();
  final db = AppDatabase.open(key);
  ref.onDispose(db.close);
  return db;
});

final apiClientProvider = Provider<ApiClient>((ref) {
  return ApiClient(
    baseUrl: apiBaseUrl,
    secureStorage: ref.watch(secureStorageProvider),
  );
});

final routerProvider = Provider((ref) => buildRouter());
