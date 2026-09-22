import uuid

from django.db import transaction
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from accounts.models import Village
from accounts.services import propose_village, serialize_village

from .models import Purchase, SyncOperation
from .services import (
    OperationError,
    cancel_purchase,
    create_purchase,
    serialize_purchase,
    update_purchase,
)

ALLOWED_TYPES = {
    "purchase.create", "purchase.update", "purchase.cancel", "village.propose",
}


class SyncView(APIView):
    """POST /api/sync — contrat figé dans dev-cacaotrack-gn.md (API-2 + API-4)."""

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "sync"

    def post(self, request):
        raw_operations = request.data.get("operations")
        if not isinstance(raw_operations, list) or not (1 <= len(raw_operations) <= 100):
            return Response(
                {"detail": "Enveloppe invalide : 'operations' doit contenir de 1 à 100 éléments."},
                status=400,
            )

        parsed = []
        for raw in raw_operations:
            op = self._parse_envelope(raw)
            if op is None:
                return Response(
                    {"detail": "Enveloppe invalide : op_id/entity_id/type manquants ou incorrects."},
                    status=400,
                )
            parsed.append(op)

        results = [self._process(request.user, op) for op in parsed]
        return Response({"server_time": timezone.now().isoformat(), "results": results}, status=200)

    @staticmethod
    def _parse_envelope(raw):
        if not isinstance(raw, dict):
            return None
        if raw.get("type") not in ALLOWED_TYPES:
            return None
        try:
            op_id = uuid.UUID(str(raw.get("op_id")))
            entity_id = uuid.UUID(str(raw.get("entity_id")))
        except (ValueError, TypeError, AttributeError):
            return None
        return {
            "op_id": op_id,
            "type": raw["type"],
            "entity_id": entity_id,
            "base_version": raw.get("base_version"),
            "reason": (raw.get("reason") or "")[:255],
            "payload": raw.get("payload") if isinstance(raw.get("payload"), dict) else {},
        }

    def _process(self, user, op) -> dict:
        existing = SyncOperation.objects.filter(op_id=op["op_id"]).first()
        if existing is not None:
            if existing.type == op["type"] and existing.entity_id == op["entity_id"]:
                return existing.result  # rejeu idempotent, tel quel
            return {"op_id": str(op["op_id"]), "status": "rejected", "code": "op_id_conflict"}

        with transaction.atomic():
            result = self._apply(user, op)
            SyncOperation.objects.create(
                op_id=op["op_id"],
                user=user,
                type=op["type"],
                entity_id=op["entity_id"],
                status=result["status"],
                code=result.get("code", ""),
                result=result,
            )
        return result

    @staticmethod
    def _apply(user, op) -> dict:
        op_id, op_type, entity_id = op["op_id"], op["type"], op["entity_id"]
        try:
            if op_type == "village.propose":
                if Village.objects.filter(id=entity_id).exists():
                    raise OperationError("already_exists")
                village = propose_village(village_id=entity_id, user=user, payload=op["payload"])
                return {
                    "op_id": str(op_id), "status": "applied", "village": serialize_village(village),
                }

            if op_type == "purchase.create":
                if Purchase.objects.filter(id=entity_id).exists():
                    raise OperationError("already_exists")
                purchase = create_purchase(purchase_id=entity_id, user=user, payload=op["payload"])
                return {
                    "op_id": str(op_id), "status": "applied", "purchase": serialize_purchase(purchase),
                }

            purchase = (
                Purchase.objects.select_for_update()
                .filter(id=entity_id, company=user.company)
                .first()
            )
            if purchase is None:
                raise OperationError("not_found")
            if op["base_version"] is None:
                raise OperationError("invalid", {"base_version": ["Champ obligatoire."]})

            if op_type == "purchase.update":
                op_status, purchase = update_purchase(
                    purchase=purchase, user=user, base_version=op["base_version"],
                    reason=op["reason"], payload=op["payload"],
                )
            else:  # purchase.cancel
                reason = op["payload"].get("reason") or op["reason"]
                op_status, purchase = cancel_purchase(
                    purchase=purchase, user=user, base_version=op["base_version"], reason=reason,
                )
            return {
                "op_id": str(op_id), "status": op_status, "purchase": serialize_purchase(purchase),
            }
        except OperationError as exc:
            result = {"op_id": str(op_id), "status": "rejected", "code": exc.code}
            if exc.errors:
                result["errors"] = exc.errors
            return result
