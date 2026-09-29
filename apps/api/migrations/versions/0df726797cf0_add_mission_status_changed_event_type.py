"""add mission_status_changed event type

Revision ID: 0df726797cf0
Revises: 47623db881b8
Create Date: 2026-09-29 12:22:46.918378

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0df726797cf0'
down_revision: Union[str, Sequence[str], None] = '47623db881b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TYPE execution_event_type ADD VALUE IF NOT EXISTS 'MISSION_STATUS_CHANGED'")


def downgrade() -> None:
    """Downgrade schema."""
    raise NotImplementedError(
        "PostgreSQL does not support removing an enum value; downgrade past this "
        "revision requires manually recreating the execution_event_type enum."
    )
