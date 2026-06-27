"""add profesional_id and auth columns

Revision ID: f3c8a2b91c4e
Revises: e4a8f2b91c3d
Create Date: 2026-06-22 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f3c8a2b91c4e'
down_revision: Union[str, Sequence[str], None] = '315acb4a4fb6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Add auth/integration columns to profesional
    op.add_column('profesional', sa.Column('email', sa.String(length=255), nullable=True))
    op.create_unique_constraint('uq_profesional_email', 'profesional', ['email'])
    op.add_column('profesional', sa.Column('password_hash', sa.String(length=255), nullable=True))
    op.add_column('profesional', sa.Column('api_key', sa.String(length=255), nullable=True))
    op.create_unique_constraint('uq_profesional_api_key', 'profesional', ['api_key'])
    op.add_column('profesional', sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column('profesional', sa.Column('google_refresh_token', sa.Text(), nullable=True))
    op.add_column('profesional', sa.Column('telegram_bot_token', sa.String(length=255), nullable=True))
    op.add_column('profesional', sa.Column('telegram_secret_token', sa.String(length=255), nullable=True))

    # 2. Add profesional_id to paciente
    op.add_column('paciente', sa.Column('profesional_id', sa.Integer(), nullable=False, server_default=sa.text('1')))
    op.create_foreign_key('fk_paciente_profesional', 'paciente', 'profesional', ['profesional_id'], ['id'], ondelete='CASCADE')

    # Drop old unique constraint on dni and add composite unique
    op.drop_constraint('paciente_dni_key', 'paciente', type_='unique')
    op.create_unique_constraint('uq_paciente_profesional_dni', 'paciente', ['profesional_id', 'dni'])

    # Remove server_default after column is added
    op.alter_column('paciente', 'profesional_id', server_default=None)

    # 3. Add profesional_id to lista_de_espera
    op.add_column('lista_de_espera', sa.Column('profesional_id', sa.Integer(), nullable=False, server_default=sa.text('1')))
    op.create_foreign_key('fk_lista_de_espera_profesional', 'lista_de_espera', 'profesional', ['profesional_id'], ['id'], ondelete='CASCADE')
    op.create_index('ix_lista_de_espera_profesional_paciente', 'lista_de_espera', ['profesional_id', 'paciente_id'], unique=False)

    op.alter_column('lista_de_espera', 'profesional_id', server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    # 3. Revert lista_de_espera
    op.drop_index('ix_lista_de_espera_profesional_paciente', table_name='lista_de_espera')
    op.drop_constraint('fk_lista_de_espera_profesional', 'lista_de_espera', type_='foreignkey')
    op.drop_column('lista_de_espera', 'profesional_id')

    # 2. Revert paciente
    op.drop_constraint('uq_paciente_profesional_dni', 'paciente', type_='unique')
    op.create_unique_constraint('paciente_dni_key', 'paciente', ['dni'])
    op.drop_constraint('fk_paciente_profesional', 'paciente', type_='foreignkey')
    op.drop_column('paciente', 'profesional_id')

    # 1. Revert profesional
    op.drop_column('profesional', 'telegram_secret_token')
    op.drop_column('profesional', 'telegram_bot_token')
    op.drop_column('profesional', 'google_refresh_token')
    op.drop_column('profesional', 'is_active')
    op.drop_constraint('uq_profesional_api_key', 'profesional', type_='unique')
    op.drop_column('profesional', 'api_key')
    op.drop_column('profesional', 'password_hash')
    op.drop_constraint('uq_profesional_email', 'profesional', type_='unique')
    op.drop_column('profesional', 'email')
