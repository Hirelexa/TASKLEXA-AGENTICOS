import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tasklexa_api.domain.enums import TaskStatus
from tasklexa_api.models.mission import Task
from tasklexa_api.schemas.mission import TaskCreate


async def create_task(session: AsyncSession, data: TaskCreate) -> Task:
    task = Task(
        mission_id=data.mission_id,
        title=data.title,
        description=data.description,
        status=TaskStatus.PENDING,
        priority=data.priority,
        required_capabilities=data.required_capabilities,
        dependencies=data.dependencies,
        assigned_agent=data.assigned_agent,
        tool_requirements=data.tool_requirements,
        expected_output=data.expected_output,
    )
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task


async def get_task(session: AsyncSession, task_id: uuid.UUID) -> Task | None:
    return await session.get(Task, task_id)


async def list_tasks_for_mission(session: AsyncSession, mission_id: uuid.UUID) -> list[Task]:
    result = await session.execute(
        select(Task).where(Task.mission_id == mission_id).order_by(Task.created_at.asc())
    )
    return list(result.scalars().all())
