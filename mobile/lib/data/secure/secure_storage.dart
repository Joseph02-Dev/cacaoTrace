import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Accès centralisé au stockage sécurisé du téléphone. Aucune autre couche
/// ne doit instancier [FlutterSecureStorage] directement (socle P6,
/// architecture-cacaotrack-gn.md).
///
/// Le PIN lui-même (haché, vérifié sur le téléphone) est géré par MOB-2 ;
/// cette classe ne porte ici que les jetons JWT, communs à tout appel API.
class AppSecureStorage {
  AppSecureStorage([FlutterSecureStorage? storage])
      : _storage = storage ??
            const FlutterSecureStorage(
              aOptions: AndroidOptions(encryptedSharedPreferences: true),
            );

  final FlutterSecureStorage _storage;

  static const _accessTokenKey = 'access_token';
  static const _refreshTokenKey = 'refresh_token';

  Future<String?> readAccessToken() => _storage.read(key: _accessTokenKey);

  Future<String?> readRefreshToken() => _storage.read(key: _refreshTokenKey);

  Future<void> saveTokens({required String access, required String refresh}) async {
    await _storage.write(key: _accessTokenKey, value: access);
    await _storage.write(key: _refreshTokenKey, value: refresh);
  }

  Future<void> clearTokens() async {
    await _storage.delete(key: _accessTokenKey);
    await _storage.delete(key: _refreshTokenKey);
  }

  /// Réservé aux autres gardiens du stockage sécurisé (ex. [DatabaseKeyProvider]).
  FlutterSecureStorage get raw => _storage;
}
