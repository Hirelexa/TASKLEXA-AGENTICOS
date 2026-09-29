import asyncio
import unittest

import httpx
from pydantic import BaseModel

from tasklexa_api.domain.errors import ProviderCallFailedError, ProviderNotConfiguredError, StructuredOutputValidationError
from tasklexa_api.integrations.openrouter.client import OpenRouterClient
from tasklexa_api.integrations.openrouter.gateway import ModelGateway
from tasklexa_api.schemas.model_gateway import ChatMessage, ModelRequest, ModelSelectionRequest, StructuredModelRequest, TokenUsage


class SamplePlan(BaseModel):
    objective: str
    steps: list[str]


def _gateway(handler, api_key: str | None = "test-key") -> tuple[ModelGateway, list[httpx.Request]]:
    calls: list[httpx.Request] = []

    def _wrapped(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return handler(request)

    transport = httpx.MockTransport(_wrapped)
    client = OpenRouterClient(api_key=api_key, transport=transport)
    return ModelGateway(api_key=api_key, client=client), calls


def _models_response(request: httpx.Request) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "data": [
                {"id": "anthropic/claude-sonnet-5", "name": "Claude Sonnet 5", "context_length": 200000, "pricing": {}}
            ]
        },
    )


def _completion_response(request: httpx.Request) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "model": "anthropic/claude-sonnet-5",
            "choices": [{"message": {"content": "hello from the mock"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        },
    )


def _structured_completion_response(request: httpx.Request) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "model": "anthropic/claude-sonnet-5",
            "choices": [
                {
                    "message": {"content": '{"objective": "test", "steps": ["a", "b"]}'},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        },
    )


def _invalid_structured_completion_response(request: httpx.Request) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "model": "anthropic/claude-sonnet-5",
            "choices": [{"message": {"content": '{"unexpected": true}'}, "finish_reason": "stop"}],
            "usage": None,
        },
    )


def _server_error_response(request: httpx.Request) -> httpx.Response:
    return httpx.Response(500, text="internal error")


class ModelGatewayNotConfiguredTests(unittest.TestCase):
    def test_health_reports_not_configured_without_key_and_makes_no_call(self) -> None:
        def _fail_if_called(request: httpx.Request) -> httpx.Response:
            raise AssertionError("no HTTP call should be made when the provider is not configured")

        gateway, calls = _gateway(_fail_if_called, api_key=None)
        health = asyncio.run(gateway.health())
        self.assertEqual(health.status, "NOT_CONFIGURED")
        self.assertEqual(calls, [])

    def test_list_models_raises_without_key(self) -> None:
        def _fail_if_called(request: httpx.Request) -> httpx.Response:
            raise AssertionError("no HTTP call should be made when the provider is not configured")

        gateway, calls = _gateway(_fail_if_called, api_key=None)
        with self.assertRaises(ProviderNotConfiguredError):
            asyncio.run(gateway.list_models())
        self.assertEqual(calls, [])

    def test_complete_raises_without_key(self) -> None:
        def _fail_if_called(request: httpx.Request) -> httpx.Response:
            raise AssertionError("no HTTP call should be made when the provider is not configured")

        gateway, calls = _gateway(_fail_if_called, api_key=None)
        request = ModelRequest(model="anthropic/claude-sonnet-5", messages=[ChatMessage(role="user", content="hi")])
        with self.assertRaises(ProviderNotConfiguredError):
            asyncio.run(gateway.complete(request))
        self.assertEqual(calls, [])


class ModelGatewayLiveShapedTests(unittest.TestCase):
    def test_health_reports_live_on_200(self) -> None:
        gateway, calls = _gateway(_models_response)
        health = asyncio.run(gateway.health())
        self.assertEqual(health.status, "LIVE")
        self.assertEqual(len(calls), 1)

    def test_health_reports_failed_on_error_status(self) -> None:
        gateway, _ = _gateway(_server_error_response)
        health = asyncio.run(gateway.health())
        self.assertEqual(health.status, "FAILED")

    def test_list_models_parses_catalog(self) -> None:
        gateway, _ = _gateway(_models_response)
        catalog = asyncio.run(gateway.list_models())
        self.assertEqual(len(catalog.models), 1)
        self.assertEqual(catalog.models[0].id, "anthropic/claude-sonnet-5")
        self.assertEqual(catalog.models[0].context_length, 200000)

    def test_list_models_raises_on_error_status(self) -> None:
        gateway, _ = _gateway(_server_error_response)
        with self.assertRaises(ProviderCallFailedError):
            asyncio.run(gateway.list_models())

    def test_complete_parses_response(self) -> None:
        gateway, calls = _gateway(_completion_response)
        request = ModelRequest(model="anthropic/claude-sonnet-5", messages=[ChatMessage(role="user", content="hi")])
        response = asyncio.run(gateway.complete(request))
        self.assertEqual(response.content, "hello from the mock")
        self.assertEqual(response.model, "anthropic/claude-sonnet-5")
        self.assertEqual(response.usage.total_tokens, 15)
        self.assertEqual(len(calls), 1)

    def test_complete_raises_on_error_status(self) -> None:
        gateway, _ = _gateway(_server_error_response)
        request = ModelRequest(model="anthropic/claude-sonnet-5", messages=[ChatMessage(role="user", content="hi")])
        with self.assertRaises(ProviderCallFailedError):
            asyncio.run(gateway.complete(request))

    def test_complete_structured_validates_matching_schema(self) -> None:
        gateway, _ = _gateway(_structured_completion_response)
        request = StructuredModelRequest(
            model="anthropic/claude-sonnet-5",
            messages=[ChatMessage(role="user", content="plan something")],
            response_schema_name="sample_plan",
        )
        result = asyncio.run(gateway.complete_structured(request, SamplePlan))
        self.assertEqual(result.data["objective"], "test")
        self.assertEqual(result.data["steps"], ["a", "b"])

    def test_complete_structured_raises_on_schema_mismatch(self) -> None:
        gateway, _ = _gateway(_invalid_structured_completion_response)
        request = StructuredModelRequest(
            model="anthropic/claude-sonnet-5",
            messages=[ChatMessage(role="user", content="plan something")],
            response_schema_name="sample_plan",
        )
        with self.assertRaises(StructuredOutputValidationError):
            asyncio.run(gateway.complete_structured(request, SamplePlan))


class ModelGatewaySelectionAndCostTests(unittest.TestCase):
    def test_select_model_requires_preferred_models(self) -> None:
        gateway, _ = _gateway(_models_response)
        with self.assertRaises(ValueError):
            gateway.select_model(ModelSelectionRequest())

    def test_select_model_picks_first_preferred_with_rest_as_fallback(self) -> None:
        gateway, _ = _gateway(_models_response)
        selected = gateway.select_model(
            ModelSelectionRequest(preferred_models=["model-a", "model-b", "model-c"])
        )
        self.assertEqual(selected.model_id, "model-a")
        self.assertEqual(selected.fallback_models, ["model-b", "model-c"])

    def test_estimate_cost_is_conservative_and_does_not_fabricate_a_number(self) -> None:
        gateway, _ = _gateway(_models_response)
        usage = TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15)
        estimate = gateway.estimate_cost(usage, "anthropic/claude-sonnet-5")
        self.assertIsNone(estimate.estimated_cost_usd)
        self.assertIn("not verified", estimate.note)


if __name__ == "__main__":
    unittest.main()
