import 'dart:io';

import 'package:drift/drift.dart';
import 'package:drift/native.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';
import 'package:sqlcipher_flutter_libs/sqlcipher_flutter_libs.dart';

import 'tables/purchase_history_table.dart';
import 'tables/purchases_table.dart';
import 'tables/sync_queue_table.dart';
import 'tables/sync_state_table.dart';
import 'tables/villages_table.dart';

part 'database.g.dart';

/// Base locale (SQLite, chiffrée SQLCipher — P1 architecture-cacaotrack-gn.md).
/// Premier schéma réellement livré : aucune base « v1 » n'a jamais été
/// déployée (MOB-1 non poussé, aucun APK distribué), donc pas de migration
/// à écrire — le schéma cible v2 (design/dev) est directement `schemaVersion 1`.
@DriftDatabase(tables: [
  Villages,
  Purchases,
  PurchaseHistoryEntries,
  SyncQueueEntries,
  SyncState,
])
class AppDatabase extends _$AppDatabase {
  AppDatabase(super.executor);

  /// [encryptionKey] est généré une seule fois à l'activation et conservé
  /// dans le stockage sécurisé du téléphone (voir [DatabaseKeyProvider]) —
  /// jamais codée en dur, jamais envoyée au serveur.
  factory AppDatabase.open(String encryptionKey) {
    return AppDatabase(_openConnection(encryptionKey));
  }

  @override
  int get schemaVersion => 1;

  @override
  MigrationStrategy get migration => MigrationStrategy(
        beforeOpen: (details) async {
          await customStatement('PRAGMA foreign_keys = ON');
        },
      );

  static QueryExecutor _openConnection(String encryptionKey) {
    return LazyDatabase(() async {
      // Nécessaire sur certaines versions Android avant l'ouverture d'une
      // base SQLCipher (voir doc du paquet sqlcipher_flutter_libs).
      await applyWorkaroundToOpenSqlCipherOnOldAndroidVersions();

      final dir = await getApplicationDocumentsDirectory();
      final file = File(p.join(dir.path, 'cacaotrack.sqlite'));

      return NativeDatabase.createInBackground(
        file,
        setup: (rawDb) {
          final escapedKey = encryptionKey.replaceAll("'", "''");
          rawDb.execute("PRAGMA key = '$escapedKey';");
          rawDb.execute('PRAGMA foreign_keys = ON;');
        },
      );
    });
  }
}
