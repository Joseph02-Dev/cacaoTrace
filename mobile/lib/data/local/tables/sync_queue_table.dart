import 'package:drift/drift.dart';

/// File d'opérations en attente d'envoi (`POST /api/v1/sync`,
/// dev-cacaotrack-gn.md). Une ligne = une opération `{op_id, type,
/// entity_id, base_version, reason, payload}` du contrat.
///
/// `type` reste un texte libre (pas d'enum Drift) : `purchase.create`,
/// `purchase.update`, `purchase.cancel` aujourd'hui, `village.propose`
/// (US-205 / P3) à partir de MOB-3, sans nouvelle migration de schéma.
class SyncQueueEntries extends Table {
  TextColumn get opId => text()(); // uuid — clé d'idempotence envoyée au serveur
  TextColumn get type => text()();
  TextColumn get entityId => text()();

  /// Obligatoire pour update/cancel, absent pour create (concurrence optimiste).
  IntColumn get baseVersion => integer().nullable()();

  /// Motif facultatif d'une modification, ≤ 255 caractères (contrat API).
  TextColumn get reason => text().nullable().withLength(max: 255)();

  TextColumn get payloadJson => text()();

  /// pending | syncing | success | error
  TextColumn get status => text().withDefault(const Constant('pending'))();
  IntColumn get attempts => integer().withDefault(const Constant(0))();
  TextColumn get lastError => text().nullable()();

  DateTimeColumn get createdAt => dateTime().withDefault(currentDateAndTime)();
  DateTimeColumn get updatedAt => dateTime().withDefault(currentDateAndTime)();

  @override
  Set<Column> get primaryKey => {opId};

  @override
  List<String> get customConstraints => [
        "CHECK (status IN ('pending', 'syncing', 'success', 'error'))",
      ];
}
