from datetime import timedelta

from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Village
from purchases.models import Purchase
from purchases.services import serialize_purchase

from .cursor import MIN_UUID, InvalidCursor, decode, encode


def _serialize_company(company):
    return {
        "id": str(company.id),
        "name": company.name,
        "standard_bag_weight_kg": str(company.standard_bag_weight_kg),
    }


def _serialize_village(village):
    return {
        "id": str(village.id),
        "name": village.name,
        "prefecture": village.prefecture,
        "latitude": str(village.latitude) if village.latitude is not None else None,
        "longitude": str(village.longitude) if village.longitude is not None else None,
        "is_active": village.status == Village.STATUS_ACTIVE,
    }


class SyncChangesView(APIView):
    """GET /api/sync/changes — contrat figé dans dev-cacaotrack-gn.md (API-3).

    Pagination par curseur composé (updated_at, id) pour une lecture exacte au sein
    d'une même série d'appels (has_more=true). Entre deux sessions de synchronisation
    distinctes, le curseur renvoyé au client est reculé de SYNC_PULL_OVERLAP_SECONDS :
    des doublons sont alors possibles (le téléphone les tolère, cf. contrat), afin de
    ne jamais rater un achat dont l'écriture se termine juste après la lecture.
    """

    def get(self, request):
        limit_raw = request.query_params.get("limit")
        limit = getattr(settings, "SYNC_DEFAULT_LIMIT", 200)
        if limit_raw is not None:
            try:
                limit = int(limit_raw)
            except ValueError:
                return Response({"detail": "Paramètre 'limit' invalide."}, status=400)
        max_limit = getattr(settings, "SYNC_MAX_LIMIT", 500)
        if not (1 <= limit <= max_limit):
            return Response(
                {"detail": f"Paramètre 'limit' doit être entre 1 et {max_limit}."}, status=400
            )

        cursor_raw = request.query_params.get("cursor")
        cursor = None
        if cursor_raw:
            try:
                cursor = decode(cursor_raw)
            except InvalidCursor:
                return Response({"detail": "Paramètre 'cursor' invalide."}, status=400)

        qs = Purchase.objects.filter(collector=request.user).select_related("village")
        if cursor is not None:
            cutoff_dt, cutoff_id = cursor
            qs = qs.filter(
                Q(updated_at__gt=cutoff_dt) | Q(updated_at=cutoff_dt, id__gt=cutoff_id)
            )
        page = list(qs.order_by("updated_at", "id")[: limit + 1])
        has_more = len(page) > limit
        page = page[:limit]

        if page:
            last = page[-1]
            if has_more:
                next_cursor = encode(last.updated_at, last.id)
            else:
                overlap = timedelta(
                    seconds=getattr(settings, "SYNC_PULL_OVERLAP_SECONDS", 120)
                )
                next_cursor = encode(last.updated_at - overlap, MIN_UUID)
        else:
            next_cursor = cursor_raw or ""

        villages = Village.objects.filter(company=request.user.company).order_by("name")

        return Response(
            {
                "server_time": timezone.now().isoformat(),
                "cursor": next_cursor,
                "has_more": has_more,
                "company": _serialize_company(request.user.company),
                "villages": [_serialize_village(v) for v in villages],
                "purchases": [serialize_purchase(p) for p in page],
            },
            status=200,
        )
