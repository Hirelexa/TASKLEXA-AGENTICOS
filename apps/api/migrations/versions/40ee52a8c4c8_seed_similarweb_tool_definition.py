"""seed similarweb tool definition

Revision ID: 40ee52a8c4c8
Revises: 5767e4723721
Create Date: 2026-09-29 13:49:18.195370

"""
import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, ENUM, UUID


# revision identifiers, used by Alembic.
revision: str = '40ee52a8c4c8'
down_revision: Union[str, Sequence[str], None] = '5767e4723721'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Deterministic id (uuid5), matching TOOL_ID in
# tasklexa_api.integrations.similarweb.tool - see docs/decisions.md ADR-020.
SIMILARWEB_TOOL_ID = "e97908ea-63f3-5886-b190-79dc3bd2b0c6"

tool_definitions_table = sa.table(
    "tool_definitions",
    sa.column("id", UUID(as_uuid=True)),
    sa.column("name", sa.Text),
    sa.column("description", sa.Text),
    sa.column("provider", sa.Text),
    sa.column("capabilities", ARRAY(sa.Text)),
    sa.column("authentication_type", sa.Text),
    sa.column("risk_level", ENUM("LOW", "MEDIUM", "HIGH", name="tool_definition_risk_level", create_type=False)),
    sa.column("requires_approval", sa.Boolean),
    sa.column(
        "status", ENUM("AVAILABLE", "NOT_CONFIGURED", "DISABLED", "FAILED", name="tool_status", create_type=False)
    ),
)


def upgrade() -> None:
    """Upgrade schema."""
    op.bulk_insert(
        tool_definitions_table,
        [
            {
                "id": uuid.UUID(SIMILARWEB_TOOL_ID),
                "name": "similarweb",
                "description": (
                    "External digital market intelligence tool: website analysis, competitor "
                    "comparison, and market signal search."
                ),
                "provider": "similarweb",
                "capabilities": [
                    "digital_market_intelligence",
                    "website_analysis",
                    "competitive_intelligence",
                ],
                "authentication_type": "api_key",
                "risk_level": "LOW",
                "requires_approval": False,
                # NOT_CONFIGURED because no SIMILARWEB_API_KEY exists in this environment.
                # This is a stored snapshot, not a live check - update this row (or replace
                # it with a fresh migration) once a real credential and confirmed MCP/REST
                # schemas exist. See docs/decisions.md ADR-020.
                "status": "NOT_CONFIGURED",
            }
        ],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        tool_definitions_table.delete().where(tool_definitions_table.c.id == uuid.UUID(SIMILARWEB_TOOL_ID))
    )
