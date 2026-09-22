"""Règles métier référentiels, testables sans HTTP (architecture §3)."""
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone

from common.errors import OperationError

from .models import User, Village


def _decimal_opt(value, field, errors, min_value=None, max_value=None):
    if value in (None, ""):
        return None
    try:
        dec = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        errors[field] = ["Valeur numérique invalide."]
        return None
    if min_value is not None and dec < min_value:
        errors[field] = [f"Doit être supérieur ou égal à {min_value}."]
    if max_value is not None and dec > max_value:
        errors[field] = [f"Doit être inférieur ou égal à {max_value}."]
    return dec


def propose_village(*, village_id, user: User, payload: dict) -> Village:
    """US-205 : un village hors liste est créé « en attente », utilisable localement
    tout de suite ; l'admin le valide ou le fusionne plus tard (P3)."""
    errors: dict = {}
    name = (payload.get("name") or "").strip()
    if not name:
        errors["name"] = ["Champ obligatoire."]
    prefecture = (payload.get("prefecture") or "").strip()
    latitude = _decimal_opt(payload.get("latitude"), "latitude", errors, Decimal("-90"), Decimal("90"))
    longitude = _decimal_opt(payload.get("longitude"), "longitude", errors, Decimal("-180"), Decimal("180"))
    if errors:
        raise OperationError("invalid", errors)

    return Village.objects.create(
        id=village_id,
        company=user.company,
        name=name,
        prefecture=prefecture,
        latitude=latitude,
        longitude=longitude,
        status=Village.STATUS_PENDING,
    )


def serialize_village(village: Village) -> dict:
    return {
        "id": str(village.id),
        "name": village.name,
        "prefecture": village.prefecture,
        "latitude": str(village.latitude) if village.latitude is not None else None,
        "longitude": str(village.longitude) if village.longitude is not None else None,
        "status": village.status,
        "merged_into": str(village.merged_into_id) if village.merged_into_id else None,
    }


def merge_village(*, source: Village, target: Village, actor: User) -> int:
    """Fusionne `source` dans `target` (déclenché par l'admin, E6/E7 — cette fonction
    est la mécanique réutilisable). Les achats de `source` sont repointés vers `target`
    et leur `updated_at` est avancé pour qu'ils repassent dans la lecture descendante
    (conséquence explicite de P3)."""
    if source.id == target.id:
        raise OperationError("invalid", {"target": ["Un village ne peut pas fusionner avec lui-même."]})
    if source.company_id != target.company_id:
        raise OperationError(
            "invalid", {"target": ["Le village cible doit appartenir à la même entreprise."]}
        )

    from purchases.models import Purchase  # import local : évite une dépendance circulaire au chargement

    with transaction.atomic():
        moved = Purchase.objects.filter(village=source).update(
            village=target, updated_at=timezone.now()
        )
        source.status = Village.STATUS_INACTIVE
        source.merged_into = target
        source.save(update_fields=["status", "merged_into", "updated_at"])
    return moved
