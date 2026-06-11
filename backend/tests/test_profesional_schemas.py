import pytest
from pydantic import ValidationError


class TestProfesionalConfigSchemas:
    def test_profesional_config_response_exists(self):
        from app.schemas.profesional import ProfesionalConfigResponse
        schema = ProfesionalConfigResponse(
            horario_inicio="08:00",
            horario_fin="18:00",
            dias_atencion=["Lunes", "Martes"],
            duracion_turno=30,
            especialidad="Odontología",
        )
        assert schema.horario_inicio == "08:00"
        assert schema.horario_fin == "18:00"
        assert schema.dias_atencion == ["Lunes", "Martes"]
        assert schema.duracion_turno == 30
        assert schema.especialidad == "Odontología"

    def test_profesional_config_update_exists(self):
        from app.schemas.profesional import ProfesionalConfigUpdate
        schema = ProfesionalConfigUpdate()
        assert schema.horario_inicio is None
        assert schema.horario_fin is None
        assert schema.dias_atencion is None
        assert schema.duracion_turno is None

    def test_profesional_config_update_partial(self):
        from app.schemas.profesional import ProfesionalConfigUpdate
        schema = ProfesionalConfigUpdate(duracion_turno=60)
        assert schema.duracion_turno == 60

    def test_profesional_config_update_invalid_horario(self):
        from app.schemas.profesional import ProfesionalConfigUpdate
        with pytest.raises(ValidationError):
            ProfesionalConfigUpdate(horario_inicio="18:00", horario_fin="08:00")

    def test_profesional_config_update_invalid_duracion(self):
        from app.schemas.profesional import ProfesionalConfigUpdate
        with pytest.raises(ValidationError):
            ProfesionalConfigUpdate(duracion_turno=0)

    def test_profesional_config_update_dias_atencion_empty(self):
        from app.schemas.profesional import ProfesionalConfigUpdate
        with pytest.raises(ValidationError):
            ProfesionalConfigUpdate(dias_atencion=[])

    def test_disponibilidad_response_exists(self):
        from app.schemas.profesional import DisponibilidadResponse
        schema = DisponibilidadResponse(horarios=["08:00", "09:00"])
        assert schema.horarios == ["08:00", "09:00"]

    def test_profesional_config_update_valid_dias(self):
        from app.schemas.profesional import ProfesionalConfigUpdate
        schema = ProfesionalConfigUpdate(dias_atencion=["Lunes", "Sábado"])
        assert schema.dias_atencion == ["Lunes", "Sábado"]

    def test_profesional_config_update_invalid_dia(self):
        from app.schemas.profesional import ProfesionalConfigUpdate
        with pytest.raises(ValidationError):
            ProfesionalConfigUpdate(dias_atencion=["Funday"])

    def test_profesional_config_update_only_horario_inicio(self):
        from app.schemas.profesional import ProfesionalConfigUpdate
        schema = ProfesionalConfigUpdate(horario_inicio="09:00")
        assert schema.horario_inicio == "09:00"
        assert schema.horario_fin is None

    def test_profesional_config_update_adyacente_horarios(self):
        from app.schemas.profesional import ProfesionalConfigUpdate
        schema = ProfesionalConfigUpdate(horario_inicio="08:00", horario_fin="08:01")
        assert schema.horario_inicio == "08:00"
        assert schema.horario_fin == "08:01"

    def test_disponibilidad_response_empty(self):
        from app.schemas.profesional import DisponibilidadResponse
        schema = DisponibilidadResponse(horarios=[])
        assert schema.horarios == []
