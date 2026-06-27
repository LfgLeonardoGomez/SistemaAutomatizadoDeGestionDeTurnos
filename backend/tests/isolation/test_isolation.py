import pytest
from datetime import date, time

from app.models.paciente import Paciente
from app.models.turno import Turno
from app.models.lista_de_espera import ListaDeEspera
from tests.conftest import make_profesional


class TestIsolationTurnos:
    """Tests de aislamiento: un profesional no puede ver/modificar turnos de otro."""

    @pytest.mark.asyncio
    async def test_get_turno_otro_profesional_404(self, authenticated_client, db_session, profesional):
        otro = make_profesional(
            nombre="Dr. B",
            dias_atencion=["Lunes"],
            email="drb@local.dev",
            password_hash="fakehash",
        )
        db_session.add(otro)
        await db_session.commit()
        await db_session.refresh(otro)

        turno = Turno(
            fecha=date(2026, 6, 15),
            hora_inicio=time(9, 0),
            hora_fin=time(9, 30),
            profesional_id=otro.id,
            estado="CONFIRMADO",
        )
        db_session.add(turno)
        await db_session.commit()
        await db_session.refresh(turno)

        response = authenticated_client.get(f"/turnos/{turno.id}")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_put_turno_otro_profesional_404(self, authenticated_client, db_session, profesional):
        otro = make_profesional(
            nombre="Dr. B",
            dias_atencion=["Lunes"],
            email="drb@local.dev",
            password_hash="fakehash",
        )
        db_session.add(otro)
        await db_session.commit()
        await db_session.refresh(otro)

        turno = Turno(
            fecha=date(2026, 6, 15),
            hora_inicio=time(9, 0),
            hora_fin=time(9, 30),
            profesional_id=otro.id,
            estado="CONFIRMADO",
        )
        db_session.add(turno)
        await db_session.commit()
        await db_session.refresh(turno)

        response = authenticated_client.put(f"/turnos/{turno.id}", json={"estado": "CANCELADO"})
        assert response.status_code == 404


class TestIsolationPacientes:
    """Tests de aislamiento: un profesional no puede ver pacientes de otro."""

    @pytest.mark.asyncio
    async def test_get_paciente_otro_profesional_404(self, authenticated_client, db_session, profesional):
        otro = make_profesional(
            nombre="Dr. B",
            dias_atencion=["Lunes"],
            email="drb@local.dev",
            password_hash="fakehash",
        )
        db_session.add(otro)
        await db_session.commit()
        await db_session.refresh(otro)

        paciente = Paciente(
            nombre="Otro", apellido="Paciente", dni="88888888", telefono="8",
            profesional_id=otro.id,
        )
        db_session.add(paciente)
        await db_session.commit()

        response = authenticated_client.get(f"/pacientes/{paciente.id}")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_paciente_turnos_otro_profesional_404(self, authenticated_client, db_session, profesional):
        otro = make_profesional(
            nombre="Dr. B",
            dias_atencion=["Lunes"],
            email="drb@local.dev",
            password_hash="fakehash",
        )
        db_session.add(otro)
        await db_session.commit()
        await db_session.refresh(otro)

        paciente = Paciente(
            nombre="Otro", apellido="Paciente", dni="88888888", telefono="8",
            profesional_id=otro.id,
        )
        db_session.add(paciente)
        await db_session.commit()

        response = authenticated_client.get(f"/pacientes/{paciente.id}/turnos")
        assert response.status_code == 404


class TestIsolationListaEspera:
    """Tests de aislamiento: un profesional no puede ver/eliminar lista de espera de otro."""

    @pytest.mark.asyncio
    async def test_delete_lista_espera_otro_profesional_404(self, authenticated_client, db_session, profesional):
        otro = make_profesional(
            nombre="Dr. B",
            dias_atencion=["Lunes"],
            email="drb@local.dev",
            password_hash="fakehash",
        )
        db_session.add(otro)
        await db_session.commit()
        await db_session.refresh(otro)

        paciente = Paciente(
            nombre="Otro", apellido="Paciente", dni="88888888", telefono="8",
            profesional_id=otro.id,
        )
        db_session.add(paciente)
        await db_session.commit()
        await db_session.refresh(paciente)

        registro = ListaDeEspera(
            paciente_id=paciente.id,
            fecha_solicitada=date(2026, 6, 15),
            profesional_id=otro.id,
        )
        db_session.add(registro)
        await db_session.commit()
        await db_session.refresh(registro)

        response = authenticated_client.delete(f"/lista-espera/{registro.id}")
        assert response.status_code == 404


class TestIsolationProfesional:
    """Tests de aislamiento: un profesional solo puede ver sus propias métricas/config."""

    @pytest.mark.asyncio
    async def test_get_configuracion_only_self(self, authenticated_client, db_session, profesional):
        response = authenticated_client.get("/profesional/configuracion")
        assert response.status_code == 200
        data = response.json()
        assert data["especialidad"] == profesional.especialidad

    @pytest.mark.asyncio
    async def test_get_metricas_only_self(self, authenticated_client, db_session, profesional):
        otro = make_profesional(
            nombre="Dr. B",
            dias_atencion=["Lunes"],
            email="drb@local.dev",
            password_hash="fakehash",
        )
        db_session.add(otro)
        await db_session.commit()
        await db_session.refresh(otro)

        hoy = date.today()
        db_session.add(Turno(
            fecha=hoy,
            hora_inicio=time(9, 0),
            hora_fin=time(9, 30),
            profesional_id=otro.id,
            estado="CONFIRMADO",
        ))
        await db_session.commit()

        response = authenticated_client.get("/profesional/metricas")
        assert response.status_code == 200
        data = response.json()
        assert data["turnos_hoy"] == 0

    @pytest.mark.asyncio
    async def test_get_turnos_hoy_only_self(self, authenticated_client, db_session, profesional):
        otro = make_profesional(
            nombre="Dr. B",
            dias_atencion=["Lunes"],
            email="drb@local.dev",
            password_hash="fakehash",
        )
        db_session.add(otro)
        await db_session.commit()
        await db_session.refresh(otro)

        hoy = date.today()
        db_session.add(Turno(
            fecha=hoy,
            hora_inicio=time(9, 0),
            hora_fin=time(9, 30),
            profesional_id=otro.id,
            estado="CONFIRMADO",
        ))
        await db_session.commit()

        response = authenticated_client.get("/profesional/turnos-hoy")
        assert response.status_code == 200
        data = response.json()
        assert data == []
