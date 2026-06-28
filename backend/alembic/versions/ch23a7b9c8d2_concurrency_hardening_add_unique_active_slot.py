"""ch23_concurrency_hardening_add_unique_active_slot

Revision ID: ch23a7b9c8d2
Revises: c22d4e6f8a0c
Create Date: 2026-06-28 00:00:00.000000

Cierra el gap R3/OQ-5 del change transaction-hardening: agrega un índice único
parcial sobre (profesional_id, fecha, hora_inicio) que solo aplica a Turnos
activos (DISPONIBLE, RESERVADO_TEMPORAL, CONFIRMADO). Esto garantiza que dos
requests concurrentes a ``reservar_turno`` no puedan crear dos Turnos para el
mismo slot.

La constraint es **parcial** (no absoluta) para permitir múltiples Turnos
CANCELADOS/COMPLETADOS en el mismo slot, preservando el historial del
profesional. La cancelación sigue siendo un UPDATE del estado (no un DELETE).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "ch23a7b9c8d2"
down_revision: Union[str, None] = "c22d4e6f8a0c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Crea el índice único parcial ``uq_turno_active_slot``."""
    op.create_index(
        "uq_turno_active_slot",
        "turno",
        ["profesional_id", "fecha", "hora_inicio"],
        unique=True,
        postgresql_where=sa.text(
            "estado IN ('DISPONIBLE', 'RESERVADO_TEMPORAL', 'CONFIRMADO')"
        ),
    )


def downgrade() -> None:
    """Elimina el índice único parcial."""
    op.drop_index("uq_turno_active_slot", table_name="turno")
