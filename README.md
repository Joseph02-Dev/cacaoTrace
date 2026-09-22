# cacaoTrace
Application mobile

## API (Django) — développement local

```bash
cd api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py test accounts
python manage.py runserver
```

Sans `DATABASE_URL` dans `.env`, la base est SQLite locale (`api/db.sqlite3`).

## Mobile (Flutter) — développement local

Cible : Flutter 3.47.5 / Dart 3.13, Android 8+ (minSdk 26).

```bash
cd mobile
flutter create .          # génère android/ (et ios/ si besoin) — une seule fois
flutter pub get
flutter gen-l10n          # génère lib/l10n/app_localizations.dart
dart run build_runner build --delete-conflicting-outputs   # génère lib/data/local/database.g.dart
flutter analyze
flutter test
flutter run --dart-define=API_BASE_URL=https://<hôte>/api/v1/
```

Sans `--dart-define=API_BASE_URL=...`, l'app pointe vers un espace réservé
(`https://CHANGE_ME.example/api/v1/`, voir `mobile/lib/app/providers.dart`)
et aucun appel réseau réel ne doit être tenté.
