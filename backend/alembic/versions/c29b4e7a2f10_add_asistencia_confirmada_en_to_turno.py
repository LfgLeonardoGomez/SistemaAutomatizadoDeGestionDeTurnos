"""c29_add_asistencia_confirmada_en_to_turno

Revision ID: c29b4e7a2f10
Revises: c27a1b3d9e40
Create Date: 2026-08-12 00:00:00.000000

Change C-29 (primera tajada): agrega `turno.asistencia_confirmada_en`
(TIMESTAMP NULL).

Registra el momento en que el paciente respondió "confirmar" al recordatorio.
NO es un estado del turno: `turno.estado` sigue siendo CONFIRMADO antes y
después, y el enum `turno_estado_enum` no se toca. Es el dato que le permite
al job de escalado distinguir a quien respondió de quien ignoró el mensaje.

Timestamp y no booleano: NULL ya expresa "no respondió" sin una columna
extra, y el escalado necesita el instante para calcular la ventana del
segundo aviso.

upgrade:
  1. Agrega `asistencia_confirmada_en TIMESTAMP NULL` a `turno`.
     Las filas existentes quedan en NULL, que es semánticamente correcto:
     ningún paciente pudo haber confirmado antes de que el botón funcionara.

downgrade:
  1. Elimina la columna.

Constraints que NO se tocan: uq_turno_active_slot, el enum de estado, ni
ningún índice existente.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = "c29b4e7a2f10"
down_revision: Union[str, None] = "c27a1b3d9e40"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "turno",
        sa.Column("asistencia_confirmada_en", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("turno", "asistencia_confirmada_en")
