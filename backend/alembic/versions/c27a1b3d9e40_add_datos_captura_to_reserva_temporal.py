"""c27_add_datos_captura_to_reserva_temporal

Revision ID: c27a1b3d9e40
Revises: c23d0e5t1nar
Create Date: 2026-08-11 00:00:00.000000

Change C-27: adds `reserva_temporal.datos_captura` (JSONB NOT NULL DEFAULT '{}').

Holds the partial answers of the Telegram capture conversation (dni, nombre,
apellido, telefono, email) between n8n executions. It lives on
`reserva_temporal` — rather than on its own table — because the conversation
is only meaningful while the slot is held: the row is already deleted on
confirmation (turno_service.confirmar_turno) and by liberar_reservas_vencidas,
so the state expires with the reservation and needs no separate TTL.

The conversation STEP is not stored: it is derived from the captured data
(captura_service.derivar_paso), so a step that contradicts the data cannot
be represented.

upgrade:
  1. Adds `datos_captura` JSONB NOT NULL DEFAULT '{}' to `reserva_temporal`.
     Existing rows backfill to '{}' via the server default.

downgrade:
  1. Drops the column.

Constraints that are NOT touched: the unique on turno_id, the
ix_reserva_temporal_expiracion index.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers
revision: str = "c27a1b3d9e40"
down_revision: Union[str, None] = "c23d0e5t1nar"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "reserva_temporal",
        sa.Column(
            "datos_captura",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("reserva_temporal", "datos_captura")
