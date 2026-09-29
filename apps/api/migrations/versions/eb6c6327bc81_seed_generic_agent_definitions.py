"""seed generic agent definitions

Revision ID: eb6c6327bc81
Revises: 0df726797cf0
Create Date: 2026-09-29 12:39:29.074548

"""
import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, ENUM, UUID


# revision identifiers, used by Alembic.
revision: str = 'eb6c6327bc81'
down_revision: Union[str, Sequence[str], None] = '0df726797cf0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Deterministic ids (uuid5, stable across environments) so this seed data is
# addressable by tests and future migrations without a live lookup.
SEED_AGENTS = [
    {
        "id": "bc1c9110-c18e-5230-97e1-c3d5b2c17611",
        "name": "research-agent",
        "description": "Gathers and summarizes external information relevant to a mission objective.",
        "capabilities": ["research", "external_intelligence", "summarization"],
    },
    {
        "id": "332ead1a-4503-597b-a81e-76c745692ab6",
        "name": "analysis-agent",
        "description": "Performs analytical and technical assessment of gathered evidence, including risk analysis.",
        "capabilities": ["analysis", "technical_analysis", "risk_analysis"],
    },
    {
        "id": "929cfb7c-3cf2-5d56-bd86-0e0549d04e35",
        "name": "planning-agent",
        "description": "Breaks a mission objective into a structured, dependency-ordered task plan.",
        "capabilities": ["planning"],
    },
    {
        "id": "903e1276-1b61-5d47-ac95-fb52033b61b4",
        "name": "verification-agent",
        "description": "Independently checks mission outputs against success criteria before completion.",
        "capabilities": ["verification"],
    },
    {
        "id": "c031c9f7-1675-539c-b317-e9542c23973a",
        "name": "market-intelligence-agent",
        "description": "Analyzes digital market presence, websites, and competitive positioning.",
        "capabilities": ["digital_market_intelligence", "website_analysis", "competitive_intelligence"],
    },
]

agent_definitions_table = sa.table(
    "agent_definitions",
    sa.column("id", UUID(as_uuid=True)),
    sa.column("name", sa.Text),
    sa.column("description", sa.Text),
    sa.column("capabilities", ARRAY(sa.Text)),
    sa.column("allowed_tools", ARRAY(sa.Text)),
    sa.column("permissions", ARRAY(sa.Text)),
    sa.column("risk_level", ENUM("LOW", "MEDIUM", "HIGH", name="agent_definition_risk_level", create_type=False)),
    sa.column("provider", sa.Text),
    sa.column(
        "status",
        ENUM("ACTIVE", "DISABLED", "DEPRECATED", name="agent_definition_status", create_type=False),
    ),
)


def upgrade() -> None:
    """Upgrade schema."""
    op.bulk_insert(
        agent_definitions_table,
        [
            {
                "id": uuid.UUID(agent["id"]),
                "name": agent["name"],
                "description": agent["description"],
                "capabilities": agent["capabilities"],
                "allowed_tools": [],
                "permissions": [],
                "risk_level": "LOW",
                "provider": "tasklexa-internal",
                "status": "ACTIVE",
            }
            for agent in SEED_AGENTS
        ],
    )


def downgrade() -> None:
    """Downgrade schema."""
    ids = [uuid.UUID(agent["id"]) for agent in SEED_AGENTS]
    op.execute(
        agent_definitions_table.delete().where(agent_definitions_table.c.id.in_(ids))
    )
