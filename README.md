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
