from django.urls import path

from .views import SyncChangesView

urlpatterns = [
    path("sync/changes", SyncChangesView.as_view(), name="sync-changes"),
]
