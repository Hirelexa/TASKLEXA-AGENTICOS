"""add task_completed event type

Revision ID: 5767e4723721
Revises: eb6c6327bc81
Create Date: 2026-09-29 13:16:15.571014

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5767e4723721'
down_revision: Union[str, Sequence[str], None] = 'eb6c6327bc81'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TYPE execution_event_type ADD VALUE IF NOT EXISTS 'TASK_COMPLETED'")


def downgrade() -> None:
    """Downgrade schema."""
    raise NotImplementedError(
        "PostgreSQL does not support removing an enum value; downgrade past this "
        "revision requires manually recreating the execution_event_type enum."
    )
