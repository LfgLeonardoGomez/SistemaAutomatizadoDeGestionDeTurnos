"""Tests para los factories de conftest.py (make_profesional, make_profesional_persisted).

Estos tests existen ANTES de aplicar masivamente el factory al resto de la suite
(ver change `fix-test-fixtures-email`). Su propósito es triangular el contrato
del factory: defaults válidos, email único, override soportado, persistencia OK.
"""
import uuid

import pytest
from sqlalchemy import select

from app.models.profesional import Profesional
from app.services.auth_service import verify_password


# ---------------------------------------------------------------------------
# make_profesional (in-memory factory, no DB)
# ---------------------------------------------------------------------------


def test_make_profesional_defaults_completos():
    """make_profesional() retorna instancia con todos los campos nullable=False no-None."""
    from tests.conftest import make_profesional

    p = make_profesional()

    assert p.nombre is not None
    assert p.especialidad is not None
    assert p.duracion_turno is not None
    assert p.horario_inicio is not None
    assert p.horario_fin is not None
    assert p.dias_atencion is not None
    assert p.email is not None
    assert p.is_active is True
    # google_calendar_id tiene server_default="primary" en la DB; en memoria es None
    # hasta flush, pero el default in-memory es opcional. Aceptamos cualquier valor
    # (None o "primary") — lo que importa es que la instancia es insertable.


def test_make_profesional_emails_son_unicos():
    """Dos invocaciones generan emails distintos (uuid-based)."""
    from tests.conftest import make_profesional

    p1 = make_profesional()
    p2 = make_profesional()

    assert p1.email != p2.email


def test_make_profesional_override():
    """Override de campos funciona: email y nombre se setean, resto usa defaults."""
    from tests.conftest import make_profesional

    p = make_profesional(email="custom@x.com", nombre="Dr. X", duracion_turno=60)

    assert p.email == "custom@x.com"
    assert p.nombre == "Dr. X"
    assert p.duracion_turno == 60
    # Defaults preservados
    assert p.especialidad == "Odontología general"
    assert p.horario_inicio == "08:00"
    assert p.horario_fin == "18:00"


def test_make_profesional_email_es_uuid_based():
    """El default email contiene un UUID hex prefix de 8 chars."""
    from tests.conftest import make_profesional

    p = make_profesional()

    # Formato esperado: "test-<8hex>@test.local"
    assert p.email.startswith("test-")
    assert p.email.endswith("@test.local")
    hex_part = p.email.removeprefix("test-").split("@")[0]
    assert len(hex_part) == 8
    int(hex_part, 16)  # debe ser hex válido


def test_make_profesional_password_hash_bcrypt_valido():
    """El password_hash default es un hash bcrypt verificable con 'test-password'."""
    from tests.conftest import make_profesional

    p = make_profesional()

    assert p.password_hash is not None
    assert p.password_hash.startswith("$2b$")
    assert verify_password("test-password", p.password_hash) is True


def test_make_profesional_campos_opcionales_none():
    """Campos opcionales son None por default (api_key, tokens)."""
    from tests.conftest import make_profesional

    p = make_profesional()

    assert p.api_key is None
    assert p.google_refresh_token is None
    assert p.telegram_bot_token is None
    assert p.telegram_secret_token is None


# ---------------------------------------------------------------------------
# make_profesional_persisted (helper que persiste en DB)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_make_profesional_persisted_asigna_id(db_session):
    """make_profesional_persisted retorna instancia con id positivo asignado."""
    from tests.conftest import make_profesional_persisted

    p = await make_profesional_persisted(db_session)

    assert p.id is not None
    assert isinstance(p.id, int)
    assert p.id > 0


@pytest.mark.asyncio
async def test_make_profesional_persisted_es_queryable(db_session):
    """Instancia persistida aparece en SELECT por email."""
    from tests.conftest import make_profesional_persisted

    p = await make_profesional_persisted(db_session, email="queryable@test.local")

    result = await db_session.execute(
        select(Profesional).where(Profesional.email == "queryable@test.local")
    )
    found = result.scalar_one()

    assert found.id == p.id
    assert found.nombre == p.nombre


@pytest.mark.asyncio
async def test_make_profesional_persisted_override(db_session):
    """Override funciona en el helper persistido."""
    from tests.conftest import make_profesional_persisted

    p = await make_profesional_persisted(
        db_session, email="override@test.local", duracion_turno=45
    )

    assert p.email == "override@test.local"
    assert p.duracion_turno == 45
    assert p.id is not None  # sigue persistido


@pytest.mark.asyncio
async def test_make_profesional_persisted_multiples_unicos(db_session):
    """Multiples invocaciones del helper no colisionan en email (unique constraint)."""
    from tests.conftest import make_profesional_persisted

    p1 = await make_profesional_persisted(db_session)
    p2 = await make_profesional_persisted(db_session)

    assert p1.id != p2.id
    assert p1.email != p2.email
