import 'package:drift/drift.dart';

/// État de synchronisation descendante — ligne unique (id = 0). Le curseur
/// correspond au paramètre `cursor` de `GET /api/v1/sync/changes`
/// (dev-cacaotrack-gn.md).
class SyncState extends Table {
  IntColumn get id => integer().withDefault(const Constant(0))();
  TextColumn get cursor => text().nullable()();
  DateTimeColumn get lastSyncAt => dateTime().nullable()();

  @override
  Set<Column> get primaryKey => {id};
}
