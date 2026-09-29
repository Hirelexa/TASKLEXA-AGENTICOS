import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from tasklexa_api.db.session import get_session
from tasklexa_api.repositories.tools import get_tool_definition, list_tool_definitions
from tasklexa_api.schemas.tool import ToolDefinitionRead

router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("", response_model=list[ToolDefinitionRead])
async def list_tools_endpoint(session: AsyncSession = Depends(get_session)) -> list[ToolDefinitionRead]:
    tools = await list_tool_definitions(session)
    return [ToolDefinitionRead.model_validate(tool) for tool in tools]


@router.get("/{tool_id}", response_model=ToolDefinitionRead)
async def get_tool_endpoint(
    tool_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> ToolDefinitionRead:
    tool = await get_tool_definition(session, tool_id)
    if tool is None:
        raise HTTPException(status_code=404, detail=f"ToolDefinition {tool_id} not found")
    return ToolDefinitionRead.model_validate(tool)
