import 'package:drift/drift.dart';

import 'villages_table.dart';

/// Achat — schéma v2 (dev-cacaotrack-gn.md, « À ajouter (schéma v2) ») :
/// ajoute `number` (attribué par le serveur), `standardBagWeightKg`,
/// `version` (concurrence optimiste) et `needsReview` par rapport au v1
/// du cahier des charges. Champs alignés sur le contrat `POST /api/v1/sync`.
@DataClassName('PurchaseRow')
class Purchases extends Table {
  TextColumn get id => text()(); // UUID généré sur le téléphone (jamais par le serveur)

  /// ACH-AAAA-NNNN, attribué par le serveur. Null tant que l'achat n'a
  /// pas été synchronisé (design-cacaotrack-gn.md v0.2).
  TextColumn get number => text().nullable()();

  TextColumn get villageId => text().references(Villages, #id)();
  TextColumn get sellerName => text()();
  TextColumn get sellerPhone => text().nullable()();

  IntColumn get bags => integer()();
  RealColumn get weightKg => real()();

  /// weighed | estimated
  TextColumn get weightMethod => text()();

  /// Poids standard utilisé si `weightMethod = estimated` — conservé sur
  /// l'achat pour la traçabilité même si le réglage change ensuite
  /// (design-cacaotrack-gn.md v0.2 : « poids standard modifiable »).
  RealColumn get standardBagWeightKg => real().nullable()();

  IntColumn get pricePerBag => integer()(); // GNF
  IntColumn get amount => integer()(); // GNF — calculé localement, confirmé par le serveur

  RealColumn get latitude => real().nullable()();
  RealColumn get longitude => real().nullable()();
  RealColumn get gpsAccuracyM => real().nullable()();
  TextColumn get gpsExemptionReason => text().nullable()();

  /// good | medium | low
  TextColumn get quality => text().nullable()();
  RealColumn get moisturePercent => real().nullable()();
  TextColumn get comment => text().nullable()();

  /// active | cancelled — état métier renvoyé par le serveur.
  TextColumn get status => text().withDefault(const Constant('active'))();
  TextColumn get cancelReason => text().nullable()();

  /// Conflit non tranché (US-504) — "À trancher".
  BoolColumn get needsReview => boolean().withDefault(const Constant(false))();

  /// Version optimiste côté serveur ; absente tant que l'achat n'a jamais
  /// été synchronisé.
  IntColumn get version => integer().nullable()();

  /// pending | syncing | synced | error — état de la file locale.
  TextColumn get syncStatus => text().withDefault(const Constant('pending'))();
  TextColumn get syncError => text().nullable()();

  DateTimeColumn get purchasedAt => dateTime()();
  DateTimeColumn get createdAt => dateTime().withDefault(currentDateAndTime)();
  DateTimeColumn get updatedAt => dateTime().withDefault(currentDateAndTime)();

  @override
  Set<Column> get primaryKey => {id};

  @override
  List<String> get customConstraints => [
        // Cahier des charges §4.2 + dev-cacaotrack-gn.md « Contraintes en base ».
        'CHECK (bags > 0)',
        'CHECK (weight_kg > 0)',
        'CHECK (price_per_bag > 0)',
        'CHECK (amount = bags * price_per_bag)',
        "CHECK (weight_method IN ('weighed', 'estimated'))",
        "CHECK (weight_method = 'weighed' OR standard_bag_weight_kg IS NOT NULL)",
        'CHECK ((latitude IS NOT NULL AND longitude IS NOT NULL) OR gps_exemption_reason IS NOT NULL)',
        'CHECK (moisture_percent IS NULL OR (moisture_percent >= 0 AND moisture_percent <= 100))',
        "CHECK (quality IS NULL OR quality IN ('good', 'medium', 'low'))",
        "CHECK (status IN ('active', 'cancelled'))",
        "CHECK (sync_status IN ('pending', 'syncing', 'synced', 'error'))",
      ];
}
