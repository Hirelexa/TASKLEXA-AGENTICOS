from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from tasklexa_api.api.agents import router as agents_router
from tasklexa_api.api.approvals import router as approvals_router
from tasklexa_api.api.decisions import router as decisions_router
from tasklexa_api.api.missions import router as missions_router
from tasklexa_api.api.tasks import orchestrator_router, router as tasks_router
from tasklexa_api.api.tools import router as tools_router
from tasklexa_api.config import get_settings
from tasklexa_api.health import HealthResponse, IntegrationsHealthResponse, collect_integration_health

settings = get_settings()

app = FastAPI(
    title="Tasklexa Agenticos API",
    summary="Tasklexa control-plane API scaffold.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(missions_router)
app.include_router(agents_router)
app.include_router(tasks_router)
app.include_router(orchestrator_router)
app.include_router(tools_router)
app.include_router(decisions_router)
app.include_router(approvals_router)


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        service=settings.service_name,
        status="LIVE",
        environment=settings.environment,
        phase="phase-11-verifier",
    )


@app.get("/health/integrations", response_model=IntegrationsHealthResponse)
async def integrations_health() -> IntegrationsHealthResponse:
    return IntegrationsHealthResponse(
        service=settings.service_name,
        integrations=await collect_integration_health(settings),
    )

