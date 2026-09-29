import asyncio
import inspect
import json
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

import httpx

from tasklexa_api.domain.errors import ProviderCallFailedError, ProviderNotConfiguredError
from tasklexa_api.integrations.band.client import WEBSOCKET_URL, BandClient
from tasklexa_api.integrations.band.ws_client import WebSocketConnector, WebSocketConnection, default_connector
from tasklexa_api.schemas.band import (
    BandEvent,
    CollaborationContext,
    EventReference,
    MessageReference,
    Participant,
    ParticipantResult,
    SubscriptionHandle,
)
from tasklexa_api.schemas.health import IntegrationHealth

PROVIDER_NAME = "Band"
EventHandler = Callable[[BandEvent], Any | Awaitable[Any]]


class BandAdapter:
    def __init__(
        self,
        api_key: str | None,
        client: BandClient | None = None,
        ws_connector: WebSocketConnector = default_connector,
    ) -> None:
        self._api_key = api_key
        self._client = client or BandClient(api_key=api_key)
        self._ws_connector = ws_connector
        self._subscriptions: dict[str, tuple[WebSocketConnection, asyncio.Task]] = {}

    def _require_configured(self) -> None:
        if not self._api_key:
            raise ProviderNotConfiguredError(PROVIDER_NAME)

    async def health(self) -> IntegrationHealth:
        if not self._api_key:
            return IntegrationHealth(
                provider=PROVIDER_NAME,
                purpose="Agent collaboration fabric",
                status="NOT_CONFIGURED",
                details="Credential is missing; no live provider calls will be attempted.",
            )

        try:
            response = await self._client.get("/contexts")
        except httpx.HTTPError as exc:
            return IntegrationHealth(
                provider=PROVIDER_NAME,
                purpose="Agent collaboration fabric",
                status="FAILED",
                details=f"Request to Band failed: {exc.__class__.__name__}",
            )

        if response.status_code in (401, 403):
            return IntegrationHealth(
                provider=PROVIDER_NAME,
                purpose="Agent collaboration fabric",
                status="FAILED",
                details=f"Authentication rejected (HTTP {response.status_code}).",
            )
        if response.status_code == 200:
            return IntegrationHealth(
                provider=PROVIDER_NAME,
                purpose="Agent collaboration fabric",
                status="LIVE",
                details="Authenticated call to GET /contexts succeeded.",
            )
        return IntegrationHealth(
            provider=PROVIDER_NAME,
            purpose="Agent collaboration fabric",
            status="FAILED",
            details=f"GET /contexts returned HTTP {response.status_code}.",
        )

    async def create_mission_context(self, mission_id: uuid.UUID, title: str) -> CollaborationContext:
        self._require_configured()
        response = await self._client.post("/contexts", json={"external_reference": str(mission_id), "title": title})
        if response.status_code not in (200, 201):
            raise ProviderCallFailedError(PROVIDER_NAME, f"POST /contexts returned HTTP {response.status_code}")
        body = response.json()
        return CollaborationContext(context_id=body["id"], mission_id=mission_id, title=title)

    async def add_participants(self, context_id: str, participants: list[Participant]) -> ParticipantResult:
        self._require_configured()
        response = await self._client.post(
            f"/contexts/{context_id}/participants",
            json={"participants": [p.model_dump() for p in participants]},
        )
        if response.status_code not in (200, 201):
            raise ProviderCallFailedError(
                PROVIDER_NAME, f"POST /contexts/{context_id}/participants returned HTTP {response.status_code}"
            )
        body = response.json()
        return ParticipantResult(
            context_id=context_id,
            added=body.get("added", [p.agent_handle for p in participants]),
            already_present=body.get("already_present", []),
        )

    async def send_task_message(
        self,
        context_id: str,
        task_id: uuid.UUID,
        target_agent: str,
        content: str,
        metadata: dict | None = None,
    ) -> MessageReference:
        self._require_configured()
        response = await self._client.post(
            f"/contexts/{context_id}/messages",
            json={
                "task_id": str(task_id),
                "target_agent": target_agent,
                "content": content,
                "metadata": metadata or {},
            },
        )
        if response.status_code not in (200, 201):
            raise ProviderCallFailedError(
                PROVIDER_NAME, f"POST /contexts/{context_id}/messages returned HTTP {response.status_code}"
            )
        body = response.json()
        return MessageReference(message_id=body["id"], context_id=context_id, task_id=task_id)

    async def send_event(
        self, context_id: str, event_type: str, content: dict, metadata: dict | None = None
    ) -> EventReference:
        self._require_configured()
        response = await self._client.post(
            f"/contexts/{context_id}/events",
            json={"event_type": event_type, "content": content, "metadata": metadata or {}},
        )
        if response.status_code not in (200, 201):
            raise ProviderCallFailedError(
                PROVIDER_NAME, f"POST /contexts/{context_id}/events returned HTTP {response.status_code}"
            )
        body = response.json()
        return EventReference(event_id=body["id"], context_id=context_id, event_type=event_type)

    async def sync_backlog(self, context_id: str) -> list[BandEvent]:
        self._require_configured()
        response = await self._client.get(f"/contexts/{context_id}/events")
        if response.status_code != 200:
            raise ProviderCallFailedError(
                PROVIDER_NAME, f"GET /contexts/{context_id}/events returned HTTP {response.status_code}"
            )
        body = response.json()
        return [
            BandEvent(event_id=row["id"], event_type=row["event_type"], content=row.get("content", {}))
            for row in body.get("data", [])
        ]

    async def subscribe(self, context_id: str, handlers: dict[str, EventHandler]) -> SubscriptionHandle:
        self._require_configured()
        connection = await self._ws_connector(f"{WEBSOCKET_URL}?token={self._api_key}&context_id={context_id}")

        async def _pump() -> None:
            async for raw_message in connection:
                try:
                    payload = json.loads(raw_message)
                except (TypeError, ValueError):
                    continue
                event = BandEvent(
                    event_id=payload.get("id", ""),
                    event_type=payload.get("event_type", ""),
                    content=payload.get("content", {}),
                )
                handler = handlers.get(event.event_type)
                if handler is None:
                    continue
                result = handler(event)
                if inspect.isawaitable(result):
                    await result

        task = asyncio.ensure_future(_pump())
        self._subscriptions[context_id] = (connection, task)
        return SubscriptionHandle(context_id=context_id, active=True)

    async def disconnect(self, context_id: str) -> None:
        entry = self._subscriptions.pop(context_id, None)
        if entry is None:
            return
        connection, task = entry
        task.cancel()
        await connection.close()

    async def aclose(self) -> None:
        for context_id in list(self._subscriptions.keys()):
            await self.disconnect(context_id)
        await self._client.aclose()
