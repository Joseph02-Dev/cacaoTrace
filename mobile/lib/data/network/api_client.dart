import 'dart:async' show unawaited;

import 'package:dio/dio.dart';
import 'package:package_info_plus/package_info_plus.dart';

import '../secure/secure_storage.dart';

/// Point d'entrée réseau unique (socle P6, architecture-cacaotrack-gn.md).
/// Aucune autre couche n'appelle `dio` directement : les futurs dépôts
/// (MOB-2 à MOB-4) passent par [ApiClient].
class ApiClient {
  ApiClient({
    required String baseUrl,
    required AppSecureStorage secureStorage,
    this.onUnauthorized,
  })  : _secureStorage = secureStorage,
        dio = Dio(BaseOptions(
          baseUrl: baseUrl, // ex. https://.../api/v1/
          connectTimeout: const Duration(seconds: 15),
          receiveTimeout: const Duration(seconds: 30),
          contentType: 'application/json',
        )) {
    dio.interceptors.add(_AuthInterceptor(
      secureStorage: _secureStorage,
      onUnauthorized: onUnauthorized,
    ));
    unawaited(_attachAppVersionHeader());
  }

  final Dio dio;
  final AppSecureStorage _secureStorage;

  /// Appelé sur une réponse 401. Le renouvellement effectif du jeton
  /// (`POST /api/v1/auth/refresh`) est câblé avec la fonctionnalité de
  /// synchronisation (MOB-4) ; ce point d'extension est posé maintenant
  /// pour que l'intercepteur n'ait pas à être retouché plus tard.
  final Future<bool> Function()? onUnauthorized;

  Future<void> _attachAppVersionHeader() async {
    // P2 (architecture) : journalisé côté serveur pour repérer les
    // téléphones restés sur une version ancienne (config/middleware.py).
    final info = await PackageInfo.fromPlatform();
    dio.options.headers['X-App-Version'] = '${info.version}+${info.buildNumber}';
  }
}

class _AuthInterceptor extends Interceptor {
  _AuthInterceptor({required this.secureStorage, this.onUnauthorized});

  final AppSecureStorage secureStorage;
  final Future<bool> Function()? onUnauthorized;

  @override
  Future<void> onRequest(RequestOptions options, RequestInterceptorHandler handler) async {
    final token = await secureStorage.readAccessToken();
    if (token != null) {
      options.headers['Authorization'] = 'Bearer $token';
    }
    handler.next(options);
  }

  @override
  Future<void> onError(DioException err, ErrorInterceptorHandler handler) async {
    if (err.response?.statusCode == 401 && onUnauthorized != null) {
      await onUnauthorized!.call();
      // Le rejeu de la requête d'origine avec le nouveau jeton est
      // implémenté avec MOB-4 (file de synchronisation).
    }
    handler.next(err);
  }
}
