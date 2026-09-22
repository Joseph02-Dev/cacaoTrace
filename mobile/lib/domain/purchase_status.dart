/// Statut affiché à l'écran, dérivé de l'état métier (serveur) et de l'état
/// de synchronisation (local) d'un achat — design-cacaotrack-gn.md v0.2,
/// section « Statuts ».
enum DisplayStatus {
  pendingSync, // "À synchroniser"
  queued, // "En attente" — opération pas encore partie (file de sync)
  syncing, // "En cours"
  synced, // "Synchronisé"
  error, // "En erreur"
  needsReview, // "À trancher"
  cancelled, // "Annulé"
}

extension DisplayStatusLabel on DisplayStatus {
  String get label => switch (this) {
        DisplayStatus.pendingSync => 'À synchroniser',
        DisplayStatus.queued => 'En attente',
        DisplayStatus.syncing => 'En cours',
        DisplayStatus.synced => 'Synchronisé',
        DisplayStatus.error => 'En erreur',
        DisplayStatus.needsReview => 'À trancher',
        DisplayStatus.cancelled => 'Annulé',
      };
}

/// Règle pure (aucune dépendance Flutter/Drift) : priorité
/// annulé > à trancher > erreur > en cours > synchronisé > à synchroniser.
/// [businessStatus] : 'active' | 'cancelled' (état serveur de l'achat).
/// [syncStatus] : 'pending' | 'syncing' | 'synced' | 'error' (file locale).
DisplayStatus purchaseDisplayStatus({
  required String businessStatus,
  required bool needsReview,
  required String syncStatus,
}) {
  if (businessStatus == 'cancelled') return DisplayStatus.cancelled;
  if (needsReview) return DisplayStatus.needsReview;
  return switch (syncStatus) {
    'error' => DisplayStatus.error,
    'syncing' => DisplayStatus.syncing,
    'synced' => DisplayStatus.synced,
    _ => DisplayStatus.pendingSync,
  };
}
