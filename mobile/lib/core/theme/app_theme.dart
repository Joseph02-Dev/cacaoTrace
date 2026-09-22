import 'package:flutter/material.dart';

import 'app_colors.dart';
import 'app_spacing.dart';
import 'app_typography.dart';

/// Thème v2, clair uniquement (design-cacaotrack-gn.md v0.2).
abstract final class AppTheme {
  static ThemeData get light {
    const colorScheme = ColorScheme.light(
      primary: AppColors.foret700, // action principale : Se connecter, Nouvel achat, Enregistrer, Synchroniser
      onPrimary: Colors.white,
      secondary: AppColors.cacao900, // bouton plein secondaire : Ouvrir le registre, Modifier, sélection
      onSecondary: Colors.white,
      surface: AppColors.surface,
      onSurface: AppColors.cacao900,
      error: AppColors.rouge,
      onError: Colors.white,
    );

    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.light,
      colorScheme: colorScheme,
      scaffoldBackgroundColor: AppColors.creme,
      fontFamily: AppTypography.fontBody,
      textTheme: const TextTheme(
        headlineSmall: AppTypography.title,
        titleMedium: AppTypography.sectionTitle,
        bodyLarge: AppTypography.bodyStrong,
        bodyMedium: AppTypography.body,
        labelSmall: AppTypography.caption,
      ),
      appBarTheme: const AppBarTheme(
        // Plus de barre de titre marron (v2) : fond crème, titre foncé à gauche.
        backgroundColor: AppColors.creme,
        foregroundColor: AppColors.cacao900,
        elevation: 0,
        centerTitle: false,
        titleTextStyle: AppTypography.title,
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: AppColors.foret700,
          foregroundColor: Colors.white,
          minimumSize: const Size.fromHeight(AppSpacing.touchTargetLarge),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppSpacing.radius),
          ),
          elevation: 0,
          textStyle: AppTypography.bodyStrong,
        ),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: AppColors.cacao900,
          foregroundColor: Colors.white,
          minimumSize: const Size.fromHeight(AppSpacing.touchTargetMin),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppSpacing.radius),
          ),
          elevation: 0,
          textStyle: AppTypography.bodyStrong,
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: AppColors.surface,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppSpacing.radius),
          borderSide: const BorderSide(color: AppColors.fieldBorder),
        ),
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      ),
      cardTheme: CardThemeData(
        color: AppColors.surface,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppSpacing.radius),
          side: const BorderSide(color: AppColors.line),
        ),
      ),
      dividerTheme: const DividerThemeData(color: AppColors.line, thickness: 1),
      navigationBarTheme: NavigationBarThemeData(
        // 4 onglets, sans pastille de fond sur l'onglet actif (v2).
        backgroundColor: AppColors.surface,
        indicatorColor: Colors.transparent,
        labelTextStyle: WidgetStateProperty.all(AppTypography.caption),
      ),
    );
  }
}
