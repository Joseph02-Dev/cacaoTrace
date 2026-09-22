import 'package:drift/drift.dart';

/// Villages reçus du serveur (bootstrap / `/api/v1/sync/changes`), plus les
/// propositions créées hors ligne (US-205, opération `village.propose`,
/// gérée à partir de MOB-3 — la colonne `status` l'anticipe déjà).
@DataClassName('VillageRow')
class Villages extends Table {
  TextColumn get id => text()();
  TextColumn get name => text().withLength(min: 1, max: 120)();
  TextColumn get prefecture => text().nullable()();
  RealColumn get latitude => real().nullable()();
  RealColumn get longitude => real().nullable()();

  /// active | pending | inactive
  TextColumn get status => text().withDefault(const Constant('active'))();

  /// Id du village cible après fusion par l'admin (P3). Les achats
  /// continuent de référencer l'ancien id ; c'est l'UI qui doit résoudre
  /// la fusion à l'affichage.
  TextColumn get mergedInto => text().nullable()();

  DateTimeColumn get updatedAt => dateTime().withDefault(currentDateAndTime)();

  @override
  Set<Column> get primaryKey => {id};

  @override
  List<String> get customConstraints => [
        "CHECK (status IN ('active', 'pending', 'inactive'))",
      ];
}
