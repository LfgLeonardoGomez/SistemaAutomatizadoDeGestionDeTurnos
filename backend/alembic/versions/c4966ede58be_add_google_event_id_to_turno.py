"""add_google_event_id_to_turno

Revision ID: c4966ede58be
Revises: 6c8e6fefc46f
Create Date: 2026-06-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4966ede58be'
down_revision: Union[str, Sequence[str], None] = '6c8e6fefc46f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('turno', sa.Column('google_event_id', sa.String(length=255), nullable=True))
    op.create_index('ix_turno_google_event_id', 'turno', ['google_event_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_turno_google_event_id', table_name='turno')
    op.drop_column('turno', 'google_event_id')
