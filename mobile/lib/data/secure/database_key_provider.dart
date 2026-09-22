import 'dart:math';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Génère et conserve la clé de chiffrement SQLCipher de la base locale
/// (P1, architecture-cacaotrack-gn.md). Créée une seule fois, à
/// l'activation du téléphone ; stockée dans le stockage sécurisé (Android
/// Keystore via flutter_secure_storage). Ne transite jamais vers le serveur.
class DatabaseKeyProvider {
  DatabaseKeyProvider(this._storage);

  static const _storageKey = 'db_encryption_key';

  final FlutterSecureStorage _storage;

  Future<String> getOrCreateKey() async {
    final existing = await _storage.read(key: _storageKey);
    if (existing != null && existing.isNotEmpty) {
      return existing;
    }
    final generated = _generateKey();
    await _storage.write(key: _storageKey, value: generated);
    return generated;
  }

  /// 256 bits, encodés en hexadécimal (format attendu par `PRAGMA key`).
  String _generateKey() {
    final random = Random.secure();
    final bytes = List<int>.generate(32, (_) => random.nextInt(256));
    return bytes.map((b) => b.toRadixString(16).padLeft(2, '0')).join();
  }
}
