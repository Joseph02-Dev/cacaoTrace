/// Grille 4 dp, marges 16, cibles 56/48 dp, rayon 12
/// (design-cacaotrack-gn.md v0.2).
abstract final class AppSpacing {
  static const double unit = 4;
  static const double pageMargin = 16;
  static const double radius = 12;
  static const double touchTargetLarge = 56; // boutons principaux
  static const double touchTargetMin = 48; // cibles minimales

  /// Pastille de statut : 14 dp minimum. Corrigé vs les 10 px de la
  /// maquette v2, illisibles en plein soleil sur téléphone d'entrée de
  /// gamme (design-cacaotrack-gn.md v0.2, « Écarts corrigés »).
  static const double statusDotSize = 14;
}
