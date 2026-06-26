"""c22 add google calendar id to profesional

Revision ID: c22d4e6f8a0c
Revises: b2d4e6f8a0c2
Create Date: 2026-06-26 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c22d4e6f8a0c"
down_revision: Union[str, None] = "b2d4e6f8a0c2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add google_calendar_id column to profesional with server default 'primary'.

    Existing rows receive 'primary' automatically via server_default.
    """
    op.add_column(
        "profesional",
        sa.Column(
            "google_calendar_id",
            sa.String(255),
            nullable=True,
            server_default="primary",
        ),
    )


def downgrade() -> None:
    """Remove google_calendar_id column from profesional."""
    op.drop_column("profesional", "google_calendar_id")
