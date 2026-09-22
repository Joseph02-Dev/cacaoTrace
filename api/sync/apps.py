from django.apps import AppConfig


class SyncConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "sync"
    label = "sync_app"  # 'sync' seul entrerait en conflit avec des noms reserves
