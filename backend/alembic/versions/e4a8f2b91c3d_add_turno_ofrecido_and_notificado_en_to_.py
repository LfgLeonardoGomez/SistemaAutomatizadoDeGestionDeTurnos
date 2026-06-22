"""add_turno_ofrecido_and_notificado_en_to_lista_de_espera

Revision ID: e4a8f2b91c3d
Revises: c4966ede58be
Create Date: 2026-06-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e4a8f2b91c3d'
down_revision: Union[str, Sequence[str], None] = 'c4966ede58be'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('lista_de_espera', sa.Column('turno_ofrecido_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_lista_de_espera_turno_ofrecido', 'lista_de_espera', 'turno', ['turno_ofrecido_id'], ['id'], ondelete='SET NULL')
    op.add_column('lista_de_espera', sa.Column('notificado_en', sa.DateTime(), nullable=True))
    op.add_column('lista_de_espera', sa.Column('telegram_chat_id', sa.String(length=50), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('lista_de_espera', 'telegram_chat_id')
    op.drop_column('lista_de_espera', 'notificado_en')
    op.drop_constraint('fk_lista_de_espera_turno_ofrecido', 'lista_de_espera', type_='foreignkey')
    op.drop_column('lista_de_espera', 'turno_ofrecido_id')
