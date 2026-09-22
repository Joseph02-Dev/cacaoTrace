import 'package:cacaotrack/domain/purchase_status.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('purchaseDisplayStatus', () {
    test('annulé prime sur tout le reste', () {
      final status = purchaseDisplayStatus(
        businessStatus: 'cancelled',
        needsReview: true,
        syncStatus: 'error',
      );
      expect(status, DisplayStatus.cancelled);
    });

    test('à trancher prime sur le statut de synchronisation', () {
      final status = purchaseDisplayStatus(
        businessStatus: 'active',
        needsReview: true,
        syncStatus: 'synced',
      );
      expect(status, DisplayStatus.needsReview);
    });

    test('reflète le statut de synchronisation sinon', () {
      expect(
        purchaseDisplayStatus(businessStatus: 'active', needsReview: false, syncStatus: 'pending'),
        DisplayStatus.pendingSync,
      );
      expect(
        purchaseDisplayStatus(businessStatus: 'active', needsReview: false, syncStatus: 'syncing'),
        DisplayStatus.syncing,
      );
      expect(
        purchaseDisplayStatus(businessStatus: 'active', needsReview: false, syncStatus: 'synced'),
        DisplayStatus.synced,
      );
      expect(
        purchaseDisplayStatus(businessStatus: 'active', needsReview: false, syncStatus: 'error'),
        DisplayStatus.error,
      );
    });
  });
}
