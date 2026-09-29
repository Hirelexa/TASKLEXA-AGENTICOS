"""execution events immutability trigger

Revision ID: 47623db881b8
Revises: fc060ed3957d
Create Date: 2026-09-29 12:01:28.287470

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '47623db881b8'
down_revision: Union[str, Sequence[str], None] = 'fc060ed3957d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        CREATE FUNCTION prevent_execution_event_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'execution_events is append-only: % on execution_events is not permitted', TG_OP;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER execution_events_immutable
        BEFORE UPDATE OR DELETE ON execution_events
        FOR EACH ROW EXECUTE FUNCTION prevent_execution_event_mutation();
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP TRIGGER IF EXISTS execution_events_immutable ON execution_events;")
    op.execute("DROP FUNCTION IF EXISTS prevent_execution_event_mutation();")
