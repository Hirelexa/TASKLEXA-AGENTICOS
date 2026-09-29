import asyncio
import unittest
import uuid

import httpx

from tasklexa_api.domain.errors import ProviderCallFailedError, ProviderNotConfiguredError
from tasklexa_api.integrations.band.adapter import BandAdapter
from tasklexa_api.integrations.band.client import BandClient
from tasklexa_api.schemas.band import BandEvent, Participant


def _adapter(handler, api_key: str | None = "test-key", ws_connector=None) -> tuple[BandAdapter, list[httpx.Request]]:
    calls: list[httpx.Request] = []

    def _wrapped(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return handler(request)

    transport = httpx.MockTransport(_wrapped)
    client = BandClient(api_key=api_key, transport=transport)
    kwargs = {"ws_connector": ws_connector} if ws_connector is not None else {}
    adapter = BandAdapter(api_key=api_key, client=client, **kwargs)
    return adapter, calls


def _contexts_200(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json={"data": []})


def _server_error(request: httpx.Request) -> httpx.Response:
    return httpx.Response(500, text="internal error")


def _unauthorized(request: httpx.Request) -> httpx.Response:
    return httpx.Response(401, json={"error": "invalid token"})


class BandAdapterNotConfiguredTests(unittest.TestCase):
    def test_health_reports_not_configured_without_key_and_makes_no_call(self) -> None:
        def _fail_if_called(request: httpx.Request) -> httpx.Response:
            raise AssertionError("no HTTP call should be made when the provider is not configured")

        adapter, calls = _adapter(_fail_if_called, api_key=None)
        health = asyncio.run(adapter.health())
        self.assertEqual(health.status, "NOT_CONFIGURED")
        self.assertEqual(calls, [])

    def test_create_mission_context_raises_without_key(self) -> None:
        def _fail_if_called(request: httpx.Request) -> httpx.Response:
            raise AssertionError("no HTTP call should be made when the provider is not configured")

        adapter, calls = _adapter(_fail_if_called, api_key=None)
        with self.assertRaises(ProviderNotConfiguredError):
            asyncio.run(adapter.create_mission_context(uuid.uuid4(), "Test Mission"))
        self.assertEqual(calls, [])

    def test_subscribe_raises_without_key(self) -> None:
        def _fail_if_called(request: httpx.Request) -> httpx.Response:
            raise AssertionError("no HTTP call should be made when the provider is not configured")

        adapter, _ = _adapter(_fail_if_called, api_key=None)
        with self.assertRaises(ProviderNotConfiguredError):
            asyncio.run(adapter.subscribe("ctx-1", {}))


class BandAdapterHealthTests(unittest.TestCase):
    def test_health_reports_live_on_200(self) -> None:
        adapter, calls = _adapter(_contexts_200)
        health = asyncio.run(adapter.health())
        self.assertEqual(health.status, "LIVE")
        self.assertEqual(len(calls), 1)

    def test_health_reports_failed_on_401(self) -> None:
        adapter, _ = _adapter(_unauthorized)
        health = asyncio.run(adapter.health())
        self.assertEqual(health.status, "FAILED")
        self.assertIn("Authentication", health.details)

    def test_health_reports_failed_on_server_error(self) -> None:
        adapter, _ = _adapter(_server_error)
        health = asyncio.run(adapter.health())
        self.assertEqual(health.status, "FAILED")


class BandAdapterRestMethodTests(unittest.TestCase):
    def test_create_mission_context_parses_response(self) -> None:
        def _handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(201, json={"id": "ctx-123"})

        adapter, calls = _adapter(_handler)
        mission_id = uuid.uuid4()
        context = asyncio.run(adapter.create_mission_context(mission_id, "Test Mission"))
        self.assertEqual(context.context_id, "ctx-123")
        self.assertEqual(context.mission_id, mission_id)
        self.assertEqual(len(calls), 1)

    def test_create_mission_context_raises_on_error_status(self) -> None:
        adapter, _ = _adapter(_server_error)
        with self.assertRaises(ProviderCallFailedError):
            asyncio.run(adapter.create_mission_context(uuid.uuid4(), "Test Mission"))

    def test_add_participants_defaults_added_list(self) -> None:
        def _handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={})

        adapter, _ = _adapter(_handler)
        result = asyncio.run(
            adapter.add_participants("ctx-1", [Participant(agent_handle="research-agent")])
        )
        self.assertEqual(result.added, ["research-agent"])
        self.assertEqual(result.already_present, [])

    def test_send_task_message_parses_reference(self) -> None:
        def _handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(201, json={"id": "msg-1"})

        adapter, calls = _adapter(_handler)
        task_id = uuid.uuid4()
        ref = asyncio.run(adapter.send_task_message("ctx-1", task_id, "research-agent", "hello"))
        self.assertEqual(ref.message_id, "msg-1")
        self.assertEqual(ref.task_id, task_id)
        body = calls[0].content
        self.assertIn(b"research-agent", body)

    def test_send_event_parses_reference(self) -> None:
        def _handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(201, json={"id": "evt-1"})

        adapter, _ = _adapter(_handler)
        ref = asyncio.run(adapter.send_event("ctx-1", "TOOL_CALLED", {"tool": "similarweb"}))
        self.assertEqual(ref.event_id, "evt-1")
        self.assertEqual(ref.event_type, "TOOL_CALLED")

    def test_sync_backlog_parses_events(self) -> None:
        def _handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200, json={"data": [{"id": "evt-1", "event_type": "THOUGHT", "content": {"text": "hmm"}}]}
            )

        adapter, _ = _adapter(_handler)
        events = asyncio.run(adapter.sync_backlog("ctx-1"))
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "THOUGHT")

    def test_sync_backlog_raises_on_error_status(self) -> None:
        adapter, _ = _adapter(_server_error)
        with self.assertRaises(ProviderCallFailedError):
            asyncio.run(adapter.sync_backlog("ctx-1"))


class FakeWebSocketConnection:
    def __init__(self, messages: list[str]) -> None:
        self._messages = messages
        self.closed = False
        self.sent: list[str] = []

    def __aiter__(self):
        return self._iter()

    async def _iter(self):
        for message in self._messages:
            yield message

    async def send(self, message: str) -> None:
        self.sent.append(message)

    async def close(self) -> None:
        self.closed = True


class BandAdapterSubscriptionTests(unittest.TestCase):
    def test_subscribe_dispatches_events_to_matching_handler(self) -> None:
        received: list[BandEvent] = []

        async def _handler(event: BandEvent) -> None:
            received.append(event)

        messages = [
            '{"id": "evt-1", "event_type": "TASK_RECORD", "content": {"task": "research"}}',
            '{"id": "evt-2", "event_type": "IGNORED_TYPE", "content": {}}',
        ]
        fake_connection = FakeWebSocketConnection(messages)

        async def _connector(url: str):
            return fake_connection

        def _fail_if_called(request: httpx.Request) -> httpx.Response:
            raise AssertionError("subscribe should not make REST calls")

        adapter, _ = _adapter(_fail_if_called, ws_connector=_connector)

        async def _run() -> None:
            handle = await adapter.subscribe("ctx-1", {"TASK_RECORD": _handler})
            self.assertTrue(handle.active)
            await asyncio.sleep(0.05)
            await adapter.disconnect("ctx-1")

        asyncio.run(_run())

        self.assertEqual(len(received), 1)
        self.assertEqual(received[0].event_id, "evt-1")
        self.assertTrue(fake_connection.closed)

    def test_disconnect_on_unknown_context_is_a_no_op(self) -> None:
        adapter, _ = _adapter(lambda r: httpx.Response(200))
        asyncio.run(adapter.disconnect("never-subscribed"))


if __name__ == "__main__":
    unittest.main()
