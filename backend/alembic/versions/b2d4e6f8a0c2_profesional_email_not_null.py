"""profesional email not null

Revision ID: b2d4e6f8a0c2
Revises: a1b2c3d4e5f6
Create Date: 2026-06-25 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2d4e6f8a0c2'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Make profesional.email NOT NULL.

    Existing NULL rows (if any) are assigned a placeholder email
    derived from their id to satisfy the NOT NULL + UNIQUE constraints.
    This is safe for development environments. Production should have
    no NULL emails after C-20 invitation-only onboarding.
    """
    # Backfill any NULL emails with a unique placeholder before altering
    op.execute(
        "UPDATE profesional SET email = 'placeholder_' || id || '@dev.local' "
        "WHERE email IS NULL"
    )
    op.alter_column(
        'profesional',
        'email',
        existing_type=sa.String(255),
        nullable=False,
    )


def downgrade() -> None:
    """Revert profesional.email to nullable."""
    op.alter_column(
        'profesional',
        'email',
        existing_type=sa.String(255),
        nullable=True,
    )
