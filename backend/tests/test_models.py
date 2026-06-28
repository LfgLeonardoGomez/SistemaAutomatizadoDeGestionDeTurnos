import pytest
from sqlalchemy.orm import DeclarativeBase

from app.models.base import Base


class TestBaseModel:
    """Tests for the SQLAlchemy DeclarativeBase."""

    def test_base_is_declarative_base(self):
        """Scenario: Base is an instance of DeclarativeBase."""
        assert isinstance(Base, type(DeclarativeBase))

    def test_base_has_metadata(self):
        """Scenario: Base exposes a metadata attribute."""
        assert hasattr(Base, "metadata")
        assert Base.metadata is not None

    def test_base_tables_populated(self):
        """Scenario: Base has all 6 model tables registered (incluye super_admin)."""
        tables = set(Base.metadata.tables.keys())
        expected = {
            "paciente",
            "profesional",
            "turno",
            "reserva_temporal",
            "lista_de_espera",
            "super_admin",
        }
        assert tables == expected
