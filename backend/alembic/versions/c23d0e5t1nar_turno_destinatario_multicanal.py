"""c23_turno_destinatario_multicanal

Revision ID: c23d0e5t1nar
Revises: ch23a7b9c8d2
Create Date: 2026-07-01 00:00:00.000000

Change C-23: introduce tabla `turno_destinatario` con ENUM `canal_notificacion_enum`
y elimina la columna muerta `paciente.telegram_chat_id`.

upgrade:
  1. Crea el tipo ENUM `canal_notificacion_enum` ('TELEGRAM', 'EMAIL').
  2. Crea la tabla `turno_destinatario` con FK CASCADE a `turno`,
     UNIQUE(turno_id, canal) y el índice ix_turno_destinatario_turno_id.
  3. Elimina la columna `paciente.telegram_chat_id` (columna muerta: nunca
     fue escrita por el backend; su único lector se refactoriza en este change).

downgrade:
  1. Re-agrega `paciente.telegram_chat_id VARCHAR(50) NULL`.
  2. Elimina la tabla `turno_destinatario`.
  3. Elimina el tipo ENUM `canal_notificacion_enum`.

Constraints que NO se tocan: uq_turno_active_slot, uq_paciente_profesional_dni.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM as postgresql_ENUM


# revision identifiers
revision: str = "c23d0e5t1nar"
down_revision: Union[str, None] = "ch23a7b9c8d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Crear el tipo ENUM explícitamente (mismo patrón que 001_create_core_tables
    #    para turno_estado_enum). Usamos la MISMA instancia de postgresql.ENUM en
    #    la columna de la tabla, y ``create_type=False`` evita la creación
    #    automática al ejecutar ``create_table`` (sin esto, Alembic reintentaría
    #    crear el tipo vía el evento ``_on_table_create`` del Enum → duplicate).
    canal_notif_enum = postgresql_ENUM(
        "TELEGRAM", "EMAIL",
        name="canal_notificacion_enum",
        create_type=False,
    )
    canal_notif_enum.create(op.get_bind(), checkfirst=True)

    # 2. Crear la tabla turno_destinatario (la columna ``canal`` referencia la
    #    instancia de arriba, así no hay creación duplicada del tipo).
    op.create_table(
        "turno_destinatario",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column(
            "turno_id",
            sa.Integer(),
            sa.ForeignKey("turno.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("canal", canal_notif_enum, nullable=False),
        sa.Column("destinatario", sa.String(255), nullable=False),
        sa.Column(
            "creado_en",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("turno_id", "canal", name="uq_turno_destinatario_canal"),
    )
    op.create_index(
        "ix_turno_destinatario_turno_id",
        "turno_destinatario",
        ["turno_id"],
    )

    # 3. Eliminar columna muerta paciente.telegram_chat_id
    op.drop_column("paciente", "telegram_chat_id")


def downgrade() -> None:
    # 1. Re-agregar paciente.telegram_chat_id (nullable, sin datos — nunca los hubo)
    op.add_column(
        "paciente",
        sa.Column("telegram_chat_id", sa.String(50), nullable=True),
    )

    # 2. Eliminar la tabla (primero el índice, luego la tabla)
    op.drop_index("ix_turno_destinatario_turno_id", table_name="turno_destinatario")
    op.drop_table("turno_destinatario")

    # 3. Eliminar el tipo ENUM (después de la tabla que lo usaba)
    canal_notif_enum = postgresql_ENUM(
        "TELEGRAM", "EMAIL",
        name="canal_notificacion_enum",
        create_type=False,
    )
    canal_notif_enum.drop(op.get_bind(), checkfirst=True)
