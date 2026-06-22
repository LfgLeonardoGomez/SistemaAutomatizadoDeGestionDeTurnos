"""add_recordatorio_enviado_to_turnos_and_telegram_chat_id_to_pacientes

Revision ID: 315acb4a4fb6
Revises: e4a8f2b91c3d
Create Date: 2026-06-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '315acb4a4fb6'
down_revision: Union[str, Sequence[str], None] = 'e4a8f2b91c3d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('turno', sa.Column('recordatorio_enviado', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.add_column('paciente', sa.Column('telegram_chat_id', sa.String(length=50), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('paciente', 'telegram_chat_id')
    op.drop_column('turno', 'recordatorio_enviado')
