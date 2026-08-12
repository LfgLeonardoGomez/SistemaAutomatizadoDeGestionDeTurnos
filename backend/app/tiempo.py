"""Local-time helpers for comparisons against appointment columns.

The database holds two kinds of time and mixing them is a silent bug:

- ``turno.fecha`` / ``turno.hora_inicio`` are ``Date`` / ``Time``: the
  appointment as a human agreed to it, in local terms.
- ``creado_en`` and ``reserva_temporal.expiracion`` are naive **UTC**, written
  through ``turno_service._utcnow_naive``.

Anything compared against the first kind must go through this module.
``date.today()`` and ``datetime.now()`` read the process clock, and the
backend container runs in UTC: between 21:00 and midnight local they already
report tomorrow, so every window derived from them is a day short. That is
not hypothetical — it is how a reminder window of "1 day + 12h" silently
became "12h" for a booking made at 22:00.

Use ``_utcnow_naive`` for durations and audit stamps; use these helpers for
anything a person would call "today" or "now".
"""

from datetime import date, datetime, timezone
from functools import lru_cache
from zoneinfo import ZoneInfo

from pydantic import ValidationError

from app.config import Settings


@lru_cache(maxsize=None)
def _zona_desde_nombre(nombre: str) -> ZoneInfo:
    return ZoneInfo(nombre)


def _nombre_zona() -> str:
    """Read the configured zone, tolerating an incomplete environment.

    ``Settings()`` validates every field, so an unrelated missing variable
    would raise here — turning a config typo into "the reminder job
    crashes". Knowing what timezone we are in does not depend on knowing the
    secret key, so the declared default is used as a fallback. The default
    is read off the model, not repeated, so there is still exactly one place
    that defines it.
    """
    try:
        return Settings().timezone
    except ValidationError:
        return str(Settings.model_fields["timezone"].default)


def _get_zona() -> ZoneInfo:
    """Resolve the application timezone.

    Kept as its own function so tests can substitute it, and so the zone
    stays configuration rather than a constant — this project's whole point
    is multi-tenancy per professional, and a professional in another
    province or country must not inherit Buenos Aires.
    """
    return _zona_desde_nombre(_nombre_zona())


def a_local(instante: datetime) -> datetime:
    """Convert an instant to local wall-clock time, naive.

    A naive ``instante`` is read as UTC, because that is what the naive
    columns of this database hold. Reading it as local would shift it twice.

    The result is naive so it can be compared against the naive columns
    directly — an aware value would raise ``can't compare offset-naive and
    offset-aware``.
    """
    if instante.tzinfo is None:
        instante = instante.replace(tzinfo=timezone.utc)
    return instante.astimezone(_get_zona()).replace(tzinfo=None)


def ahora_local() -> datetime:
    """``now`` in the application timezone, naive."""
    return a_local(datetime.now(timezone.utc))


def hoy_local() -> date:
    """``today`` in the application timezone."""
    return ahora_local().date()
