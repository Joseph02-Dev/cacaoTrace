import 'package:flutter/material.dart';

import '../../domain/purchase_status.dart';
import '../theme/app_colors.dart';
import '../theme/app_spacing.dart';
import '../theme/app_typography.dart';

/// Pastille de statut (achat ou opération de la file de synchronisation).
/// design-cacaotrack-gn.md v0.2 : icône + couleur + texte.
class StatusBadge extends StatelessWidget {
  const StatusBadge({super.key, required this.status});

  final DisplayStatus status;

  @override
  Widget build(BuildContext context) {
    final palette = _paletteFor(status);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: palette.background,
        borderRadius: BorderRadius.circular(999),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: AppSpacing.statusDotSize,
            height: AppSpacing.statusDotSize,
            decoration: BoxDecoration(
              color: palette.foreground,
              shape: BoxShape.circle,
            ),
          ),
          const SizedBox(width: 6),
          Text(
            status.label,
            style: AppTypography.caption.copyWith(color: palette.foreground),
          ),
        ],
      ),
    );
  }

  _StatusPalette _paletteFor(DisplayStatus status) {
    return switch (status) {
      DisplayStatus.pendingSync => const _StatusPalette(AppColors.ambre, AppColors.ambreBg),
      DisplayStatus.queued => const _StatusPalette(AppColors.muted, AppColors.gris),
      DisplayStatus.syncing => const _StatusPalette(AppColors.bleu, AppColors.bleuBg),
      DisplayStatus.synced => const _StatusPalette(AppColors.foret700, AppColors.foretBg),
      DisplayStatus.error => const _StatusPalette(AppColors.rouge, AppColors.rougeBg),
      DisplayStatus.needsReview => const _StatusPalette(AppColors.violet, AppColors.violetBg),
      DisplayStatus.cancelled => const _StatusPalette(AppColors.muted, AppColors.gris),
    };
  }
}

class _StatusPalette {
  const _StatusPalette(this.foreground, this.background);
  final Color foreground;
  final Color background;
}
