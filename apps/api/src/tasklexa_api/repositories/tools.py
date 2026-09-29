import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tasklexa_api.domain.enums import ToolStatus
from tasklexa_api.models.tool import ToolDefinition


async def list_tool_definitions(session: AsyncSession, available_only: bool = False) -> list[ToolDefinition]:
    query = select(ToolDefinition).order_by(ToolDefinition.name.asc())
    if available_only:
        query = query.where(ToolDefinition.status == ToolStatus.AVAILABLE)
    result = await session.execute(query)
    return list(result.scalars().all())


async def get_tool_definition(session: AsyncSession, tool_id: uuid.UUID) -> ToolDefinition | None:
    return await session.get(ToolDefinition, tool_id)
