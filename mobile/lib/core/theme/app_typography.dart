import 'package:flutter/material.dart';

/// Manrope (texte courant) + Bricolage Grotesque (titres, montants).
/// Fichiers embarqués dans l'app (assets/fonts) — aucun téléchargement à
/// l'exécution (design-cacaotrack-gn.md v0.2).
abstract final class AppTypography {
  static const fontBody = 'Manrope';
  static const fontDisplay = 'BricolageGrotesque';

  /// Carte de résumé, montant total — la plus grosse taille de l'app.
  static const TextStyle amount = TextStyle(
    fontFamily: fontDisplay,
    fontWeight: FontWeight.w700,
    fontSize: 28,
    height: 1.2,
  );

  static const TextStyle title = TextStyle(
    fontFamily: fontDisplay,
    fontWeight: FontWeight.w700,
    fontSize: 20,
    height: 1.25,
  );

  static const TextStyle sectionTitle = TextStyle(
    fontFamily: fontDisplay,
    fontWeight: FontWeight.w600,
    fontSize: 16,
    height: 1.3,
  );

  static const TextStyle body = TextStyle(
    fontFamily: fontBody,
    fontWeight: FontWeight.w400,
    fontSize: 15,
    height: 1.4,
  );

  static const TextStyle bodyStrong = TextStyle(
    fontFamily: fontBody,
    fontWeight: FontWeight.w700,
    fontSize: 15,
    height: 1.4,
  );

  static const TextStyle caption = TextStyle(
    fontFamily: fontBody,
    fontWeight: FontWeight.w400,
    fontSize: 13,
    height: 1.3,
  );
}
