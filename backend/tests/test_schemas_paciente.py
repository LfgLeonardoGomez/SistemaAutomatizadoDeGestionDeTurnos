import pytest
from datetime import date, time, datetime
from pydantic import ValidationError

from app.schemas.paciente import PacienteCreate, PacienteRead, PacienteConHistorial, TurnoRead


class TestPacienteSchemas:
    """Tests de validación de schemas Pydantic — Task 1.2."""

    def test_paciente_create_valid(self):
        """Scenario: Creación con datos válidos."""
        data = PacienteCreate(
            nombre="Juan", apellido="Pérez", dni="12345678", telefono="+54 9 11 1234-5678"
        )
        assert data.nombre == "Juan"
        assert data.apellido == "Pérez"
        assert data.dni == "12345678"
        assert data.telefono == "+54 9 11 1234-5678"

    def test_paciente_create_missing_nombre(self):
        """Scenario: Falta nombre → 422."""
        with pytest.raises(ValidationError) as exc:
            PacienteCreate(apellido="Pérez", dni="12345678", telefono="1")
        assert "nombre" in str(exc.value)

    def test_paciente_create_missing_apellido(self):
        """Scenario: Falta apellido → 422."""
        with pytest.raises(ValidationError) as exc:
            PacienteCreate(nombre="Juan", dni="12345678", telefono="1")
        assert "apellido" in str(exc.value)

    def test_paciente_create_missing_dni(self):
        """Scenario: Falta DNI → 422."""
        with pytest.raises(ValidationError) as exc:
            PacienteCreate(nombre="Juan", apellido="Pérez", telefono="1")
        assert "dni" in str(exc.value)

    def test_paciente_create_missing_telefono(self):
        """Scenario: Falta teléfono → 422."""
        with pytest.raises(ValidationError) as exc:
            PacienteCreate(nombre="Juan", apellido="Pérez", dni="12345678")
        assert "telefono" in str(exc.value)

    def test_paciente_read_from_model(self):
        """Scenario: Serializar modelo Paciente a PacienteRead."""
        # Simulamos un objeto ORM-like con atributos
        class FakePaciente:
            id = 1
            nombre = "Ana"
            apellido = "García"
            dni = "33333333"
            telefono = "4"
            creado_en = datetime(2026, 6, 1, 10, 0, 0)

        read = PacienteRead.model_validate(FakePaciente())
        assert read.id == 1
        assert read.nombre == "Ana"
        assert read.dni == "33333333"

    def test_paciente_con_historial_empty_turnos(self):
        """Scenario: Paciente sin turnos."""
        read = PacienteConHistorial(
            id=1,
            nombre="Ana",
            apellido="García",
            dni="33333333",
            telefono="4",
            creado_en=datetime(2026, 6, 1, 10, 0, 0),
            turnos=[],
        )
        assert read.turnos == []

    def test_paciente_con_historial_with_turnos(self):
        """Scenario: Paciente con turnos en historial."""
        turno = TurnoRead(
            id=10,
            fecha=date(2026, 6, 15),
            hora_inicio=time(9, 0),
            hora_fin=time(9, 30),
            estado="CONFIRMADO",
            profesional_id=1,
            paciente_id=1,
            creado_en=datetime(2026, 6, 10, 10, 0, 0),
        )
        read = PacienteConHistorial(
            id=1,
            nombre="Ana",
            apellido="García",
            dni="33333333",
            telefono="4",
            creado_en=datetime(2026, 6, 1, 10, 0, 0),
            turnos=[turno],
        )
        assert len(read.turnos) == 1
        assert read.turnos[0].estado == "CONFIRMADO"
