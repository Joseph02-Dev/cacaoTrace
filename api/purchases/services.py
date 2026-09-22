"""Règles métier de la synchronisation montante, testables sans HTTP
(architecture §3 : « aucune règle métier dans les vues »).
"""
import re
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from accounts.models import User, Village

from .models import Purchase, PurchaseHistory, PurchaseSequence

PHONE_RE = re.compile(r"^\+224[67]\d{8}$")


class OperationError(Exception):
    """Rejet définitif d'une opération : code + erreurs par champ."""

    def __init__(self, code: str, errors: dict | None = None):
        self.code = code
        self.errors = errors or {}
        super().__init__(code)


def normalize_guinea_phone(raw: str) -> str:
    digits = re.sub(r"\D", "", raw)
    if digits.startswith("224"):
        digits = digits[3:]
    candidate = f"+224{digits}"
    if not PHONE_RE.match(candidate):
        raise ValueError("format invalide")
    return candidate


def _decimal(value, field, errors, *, required=False, min_value=None, max_value=None):
    if value in (None, ""):
        if required:
            errors[field] = ["Champ obligatoire."]
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


def validate_payload(payload: dict, company, *, is_create: bool) -> tuple[dict, dict]:
    """Retourne (données nettoyées, erreurs par champ). Les erreurs bloquent l'opération."""
    errors: dict = {}
    cleaned: dict = {}

    village_id = payload.get("village_id")
    village = None
    if not village_id:
        errors["village_id"] = ["Champ obligatoire."]
    else:
        village = Village.objects.filter(
            id=village_id, company=company
        ).exclude(status=Village.STATUS_INACTIVE).first()
        if village is None:
            errors["village_id"] = ["Village introuvable pour cette entreprise."]
    cleaned["village"] = village

    seller_name = (payload.get("seller_name") or "").strip()
    if not seller_name:
        errors["seller_name"] = ["Champ obligatoire."]
    cleaned["seller_name"] = seller_name

    seller_phone = (payload.get("seller_phone") or "").strip()
    if seller_phone:
        try:
            seller_phone = normalize_guinea_phone(seller_phone)
        except ValueError:
            errors["seller_phone"] = ["Format guinéen invalide."]
    cleaned["seller_phone"] = seller_phone

    bags = payload.get("bags")
    if not isinstance(bags, int) or bags <= 0:
        errors["bags"] = ["Doit être un entier strictement supérieur à zéro."]
    cleaned["bags"] = bags

    weight_method = payload.get("weight_method")
    if weight_method not in (Purchase.WEIGHT_WEIGHED, Purchase.WEIGHT_ESTIMATED):
        errors["weight_method"] = ["Doit être 'weighed' ou 'estimated'."]
    cleaned["weight_method"] = weight_method

    weight_kg = _decimal(payload.get("weight_kg"), "weight_kg", errors, required=True, min_value=Decimal("0.01"))
    cleaned["weight_kg"] = weight_kg

    standard_bag_weight_kg = None
    if weight_method == Purchase.WEIGHT_ESTIMATED:
        standard_bag_weight_kg = _decimal(
            payload.get("standard_bag_weight_kg"), "standard_bag_weight_kg", errors,
            required=True, min_value=Decimal("0.01"),
        )
        if (
            standard_bag_weight_kg is not None
            and isinstance(bags, int) and bags > 0
            and weight_kg is not None
        ):
            expected = (standard_bag_weight_kg * bags).quantize(Decimal("0.01"))
            if weight_kg != expected:
                errors["weight_kg"] = [
                    f"Doit être exactement sacs × poids standard ({expected})."
                ]
    cleaned["standard_bag_weight_kg"] = standard_bag_weight_kg

    price_per_bag = payload.get("price_per_bag")
    if not isinstance(price_per_bag, int) or price_per_bag <= 0:
        errors["price_per_bag"] = ["Doit être un entier strictement supérieur à zéro."]
    cleaned["price_per_bag"] = price_per_bag

    latitude = payload.get("latitude")
    longitude = payload.get("longitude")
    has_gps = latitude is not None and longitude is not None
    gps_exemption_reason = (payload.get("gps_exemption_reason") or "").strip()
    if not has_gps and not gps_exemption_reason:
        errors["gps_exemption_reason"] = ["Obligatoire en l'absence de position GPS."]
    cleaned["latitude"] = _decimal(latitude, "latitude", errors, min_value=Decimal("-90"), max_value=Decimal("90")) if has_gps else None
    cleaned["longitude"] = _decimal(longitude, "longitude", errors, min_value=Decimal("-180"), max_value=Decimal("180")) if has_gps else None
    cleaned["gps_accuracy_m"] = _decimal(payload.get("gps_accuracy_m"), "gps_accuracy_m", errors, min_value=Decimal("0"))
    cleaned["gps_exemption_reason"] = "" if has_gps else gps_exemption_reason

    quality = payload.get("quality") or ""
    if quality and quality not in dict(Purchase.QUALITY_CHOICES):
        errors["quality"] = ["Valeur invalide."]
    cleaned["quality"] = quality

    cleaned["moisture_percent"] = _decimal(
        payload.get("moisture_percent"), "moisture_percent", errors,
        min_value=Decimal("0"), max_value=Decimal("100"),
    )
    cleaned["comment"] = (payload.get("comment") or "").strip()

    if is_create:
        raw_purchased_at = payload.get("purchased_at")
        purchased_at = parse_datetime(raw_purchased_at) if raw_purchased_at else None
        if purchased_at is None:
            errors["purchased_at"] = ["Date/heure invalide ou manquante."]
        elif timezone.is_naive(purchased_at):
            purchased_at = timezone.make_aware(purchased_at, timezone.utc)
        cleaned["purchased_at"] = purchased_at

    return cleaned, errors


def _amount(bags: int, price_per_bag: int) -> int:
    return bags * price_per_bag


def _clock_skew(purchased_at) -> bool:
    threshold = timezone.timedelta(hours=getattr(settings, "CLOCK_SKEW_HOURS", 24))
    return abs(timezone.now() - purchased_at) > threshold


def _diff(purchase: Purchase, cleaned: dict) -> dict:
    changes = {}
    field_map = {
        "village": ("village_id", lambda v: str(v.id) if v else None),
        "seller_name": ("seller_name", str),
        "seller_phone": ("seller_phone", str),
        "bags": ("bags", int),
        "weight_kg": ("weight_kg", str),
        "weight_method": ("weight_method", str),
        "standard_bag_weight_kg": ("standard_bag_weight_kg", lambda v: str(v) if v is not None else None),
        "price_per_bag": ("price_per_bag", int),
        "latitude": ("latitude", lambda v: str(v) if v is not None else None),
        "longitude": ("longitude", lambda v: str(v) if v is not None else None),
        "gps_accuracy_m": ("gps_accuracy_m", lambda v: str(v) if v is not None else None),
        "gps_exemption_reason": ("gps_exemption_reason", str),
        "quality": ("quality", str),
        "moisture_percent": ("moisture_percent", lambda v: str(v) if v is not None else None),
        "comment": ("comment", str),
    }
    for attr, (label, fmt) in field_map.items():
        old_value = getattr(purchase, attr)
        old = str(old_value.id) if attr == "village" else old_value
        new_raw = cleaned[attr]
        old_fmt = fmt(old_value)
        new_fmt = fmt(new_raw)
        if old_fmt != new_fmt:
            changes[label] = {"old": old_fmt, "new": new_fmt}
    return changes


def create_purchase(*, purchase_id, user: User, payload: dict) -> Purchase:
    cleaned, errors = validate_payload(payload, user.company, is_create=True)
    if errors:
        raise OperationError("invalid", errors)

    year = cleaned["purchased_at"].year
    number = f"ACH-{year}-{PurchaseSequence.next_number(user.company, year):04d}"

    purchase = Purchase.objects.create(
        id=purchase_id,
        company=user.company,
        collector=user,
        village=cleaned["village"],
        number=number,
        seller_name=cleaned["seller_name"],
        seller_phone=cleaned["seller_phone"],
        bags=cleaned["bags"],
        weight_kg=cleaned["weight_kg"],
        weight_method=cleaned["weight_method"],
        standard_bag_weight_kg=cleaned["standard_bag_weight_kg"],
        price_per_bag=cleaned["price_per_bag"],
        amount=_amount(cleaned["bags"], cleaned["price_per_bag"]),
        latitude=cleaned["latitude"],
        longitude=cleaned["longitude"],
        gps_accuracy_m=cleaned["gps_accuracy_m"],
        gps_exemption_reason=cleaned["gps_exemption_reason"],
        quality=cleaned["quality"],
        moisture_percent=cleaned["moisture_percent"],
        comment=cleaned["comment"],
        purchased_at=cleaned["purchased_at"],
        clock_skew_flagged=_clock_skew(cleaned["purchased_at"]),
        version=1,
    )
    PurchaseHistory.objects.create(
        purchase=purchase, action=PurchaseHistory.ACTION_CREATE, user=user,
    )
    return purchase


def update_purchase(*, purchase: Purchase, user: User, base_version: int, reason: str, payload: dict):
    """Retourne ('applied', purchase) ou ('conflict', purchase) — jamais d'exception pour un conflit."""
    if purchase.status == Purchase.STATUS_CANCELLED:
        raise OperationError("cancelled")
    if user.role == User.ROLE_COLLECTOR:
        if purchase.collector_id != user.id:
            raise OperationError("not_found")
    elif not reason or not reason.strip():
        # US-402 : correction par superviseur/admin, motif obligatoire.
        raise OperationError("invalid", {"reason": ["Motif obligatoire pour une correction."]})

    cleaned, errors = validate_payload(payload, user.company, is_create=False)
    if errors:
        raise OperationError("invalid", errors)

    if base_version != purchase.version:
        changes = _diff(purchase, cleaned)
        PurchaseHistory.objects.create(
            purchase=purchase, action=PurchaseHistory.ACTION_CONFLICT, user=user,
            reason=reason, changes=changes,
        )
        purchase.needs_review = True
        purchase.save(update_fields=["needs_review"])
        return "conflict", purchase

    changes = _diff(purchase, cleaned)
    purchase.village = cleaned["village"]
    purchase.seller_name = cleaned["seller_name"]
    purchase.seller_phone = cleaned["seller_phone"]
    purchase.bags = cleaned["bags"]
    purchase.weight_kg = cleaned["weight_kg"]
    purchase.weight_method = cleaned["weight_method"]
    purchase.standard_bag_weight_kg = cleaned["standard_bag_weight_kg"]
    purchase.price_per_bag = cleaned["price_per_bag"]
    purchase.amount = _amount(cleaned["bags"], cleaned["price_per_bag"])
    purchase.latitude = cleaned["latitude"]
    purchase.longitude = cleaned["longitude"]
    purchase.gps_accuracy_m = cleaned["gps_accuracy_m"]
    purchase.gps_exemption_reason = cleaned["gps_exemption_reason"]
    purchase.quality = cleaned["quality"]
    purchase.moisture_percent = cleaned["moisture_percent"]
    purchase.comment = cleaned["comment"]
    purchase.version += 1
    purchase.save()

    if changes:
        PurchaseHistory.objects.create(
            purchase=purchase, action=PurchaseHistory.ACTION_UPDATE, user=user,
            reason=reason, changes=changes,
        )
    return "applied", purchase


def cancel_purchase(*, purchase: Purchase, user: User, base_version: int, reason: str):
    if purchase.status == Purchase.STATUS_CANCELLED:
        raise OperationError("already_cancelled")
    if purchase.collector_id != user.id and user.role == User.ROLE_COLLECTOR:
        raise OperationError("not_found")
    if not reason or not reason.strip():
        raise OperationError("invalid", {"reason": ["Motif obligatoire."]})

    if base_version != purchase.version:
        PurchaseHistory.objects.create(
            purchase=purchase, action=PurchaseHistory.ACTION_CONFLICT, user=user,
            reason=reason, changes={"status": {"old": purchase.status, "new": "cancel proposé"}},
        )
        purchase.needs_review = True
        purchase.save(update_fields=["needs_review"])
        return "conflict", purchase

    purchase.status = Purchase.STATUS_CANCELLED
    purchase.cancel_reason = reason.strip()
    purchase.version += 1
    purchase.save()
    PurchaseHistory.objects.create(
        purchase=purchase, action=PurchaseHistory.ACTION_CANCEL, user=user, reason=reason.strip(),
    )
    return "applied", purchase


def serialize_purchase(purchase: Purchase) -> dict:
    def dec(value):
        return str(value) if value is not None else None

    return {
        "id": str(purchase.id),
        "number": purchase.number,
        "village_id": str(purchase.village_id),
        "collector_id": str(purchase.collector_id),
        "seller_name": purchase.seller_name,
        "seller_phone": purchase.seller_phone,
        "bags": purchase.bags,
        "weight_kg": dec(purchase.weight_kg),
        "weight_method": purchase.weight_method,
        "standard_bag_weight_kg": dec(purchase.standard_bag_weight_kg),
        "price_per_bag": purchase.price_per_bag,
        "amount": purchase.amount,
        "latitude": dec(purchase.latitude),
        "longitude": dec(purchase.longitude),
        "gps_accuracy_m": dec(purchase.gps_accuracy_m),
        "gps_exemption_reason": purchase.gps_exemption_reason,
        "quality": purchase.quality,
        "moisture_percent": dec(purchase.moisture_percent),
        "comment": purchase.comment,
        "status": purchase.status,
        "cancel_reason": purchase.cancel_reason,
        "needs_review": purchase.needs_review,
        "version": purchase.version,
        "purchased_at": purchase.purchased_at.isoformat(),
        "created_at": purchase.created_at.isoformat(),
        "updated_at": purchase.updated_at.isoformat(),
        "history": [
            {
                "id": h.id,
                "action": h.action,
                "at": h.at.isoformat(),
                "user_name": h.user.name if h.user else None,
                "reason": h.reason,
                "changes": h.changes,
            }
            for h in purchase.history.all()
        ],
    }
