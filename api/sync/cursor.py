import base64
import uuid
from datetime import datetime

from django.utils.dateparse import parse_datetime

# UUID minimal : sert de borne basse quand seul l'horodatage est connu
# (curseur "grossier" conservé entre deux sessions de synchronisation, cf. decode/encode_coarse).
MIN_UUID = uuid.UUID(int=0)


class InvalidCursor(Exception):
    pass


def encode(when: datetime, entity_id: uuid.UUID) -> str:
    raw = f"{when.isoformat()}|{entity_id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def decode(cursor: str) -> tuple[datetime, uuid.UUID]:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode()).decode()
        when_str, id_str = raw.split("|", 1)
        when = parse_datetime(when_str)
        entity_id = uuid.UUID(id_str)
    except Exception as exc:  # décodage, format, UUID... tout est une erreur de curseur
        raise InvalidCursor from exc
    if when is None:
        raise InvalidCursor
    return when, entity_id
