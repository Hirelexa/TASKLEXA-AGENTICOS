import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from tasklexa_api.db.session import get_session
from tasklexa_api.repositories.evidence import get_evidence, list_evidence_for_mission
from tasklexa_api.repositories.missions import get_mission
from tasklexa_api.schemas.evidence import EvidenceRead

router = APIRouter(prefix="/missions/{mission_id}/evidence", tags=["evidence"])


@router.get("", response_model=list[EvidenceRead])
async def list_evidence_endpoint(
    mission_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> list[EvidenceRead]:
    mission = await get_mission(session, mission_id)
    if mission is None:
        raise HTTPException(status_code=404, detail=f"Mission {mission_id} not found")
    evidence = await list_evidence_for_mission(session, mission_id)
    return [EvidenceRead.model_validate(item) for item in evidence]


@router.get("/{evidence_id}", response_model=EvidenceRead)
async def get_evidence_endpoint(
    mission_id: uuid.UUID, evidence_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> EvidenceRead:
    evidence = await get_evidence(session, evidence_id)
    if evidence is None or evidence.mission_id != mission_id:
        raise HTTPException(status_code=404, detail=f"Evidence {evidence_id} not found in mission {mission_id}")
    return EvidenceRead.model_validate(evidence)
