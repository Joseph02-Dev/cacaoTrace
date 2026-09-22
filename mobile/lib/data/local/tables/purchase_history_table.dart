import 'package:drift/drift.dart';

import 'purchases_table.dart';

/// Historique d'un achat, reçu du serveur (`purchase.history[]` du contrat
/// `/api/v1/sync` et `/api/v1/sync/changes` — dev-cacaotrack-gn.md) et
/// affiché tel quel dans l'écran Détail. Ajout seul, jamais modifié.
@DataClassName('PurchaseHistoryRow')
class PurchaseHistoryEntries extends Table {
  TextColumn get id => text()(); // id serveur
  TextColumn get purchaseId => text().references(Purchases, #id)();

  /// create | update | cancel | conflict
  TextColumn get action => text()();
  DateTimeColumn get at => dateTime()();
  TextColumn get userName => text()();
  TextColumn get reason => text().nullable()();

  /// JSON brut du serveur : `{champ: {old, new}}`. Pour un conflit, montre
  /// la proposition refusée.
  TextColumn get changesJson => text().nullable()();

  @override
  Set<Column> get primaryKey => {id};

  @override
  List<String> get customConstraints => [
        "CHECK (action IN ('create', 'update', 'cancel', 'conflict'))",
      ];
}
