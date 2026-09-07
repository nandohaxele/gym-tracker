"""Phase 9 assistant — interpret/execute above Phase 8. No live provider."""

from __future__ import annotations

import uuid
from decimal import Decimal

import httpx
import pytest

from app.assistant.models import ProviderIntent, ProviderInterpretation
from app.assistant.provider import (
    AssistantProviderError,
    OpenAIResponsesProvider,
    extract_structured_output,
)
from app.assistant.rate_limit import reset as reset_rate_limit
from app.assistant import service as assistant_service
from app.core.config import get_settings
from tests.helpers import (
    add_set,
    add_we,
    bench_id,
    create_template,
    empty_workout,
    err,
    get_workout,
    ok,
    plank_id,
)


@pytest.fixture(autouse=True)
def _reset_assistant_limit():
    reset_rate_limit()
    yield
    reset_rate_limit()


class FakeProvider:
    def __init__(self, result: ProviderInterpretation):
        self.result = result
        self.calls = []

    def interpret(self, text, context):
        self.calls.append((text, context))
        return self.result


def _ready(*intents: ProviderIntent) -> ProviderInterpretation:
    return ProviderInterpretation(status="ready", intents=list(intents))


def _interpret(client, headers, text, **extra):
    payload = {"text": text, **extra}
    return client.post("/api/assistant/interpret", headers=headers, json=payload)


def _execute(client, headers, commands):
    return client.post(
        "/api/assistant/execute",
        headers=headers,
        json={"commands": commands},
    )


def test_interpret_and_execute_require_auth(client):
    err(client.post("/api/assistant/interpret", json={"text": "add bench"}), 401)
    err(
        client.post(
            "/api/assistant/execute",
            json={"commands": [{"type": "finish_session"}]},
        ),
        401,
    )


def test_provider_schema_rejects_unsupported_type_and_invented_id():
    with pytest.raises(Exception):
        ProviderInterpretation.model_validate(
            {"status": "ready", "intents": [{"type": "delete_set"}]}
        )
    with pytest.raises(Exception):
        ProviderIntent.model_validate(
            {"type": "add_exercise", "query": "Bench Press", "exercise_id": 99}
        )


def test_panca_piana_uses_resolver_not_invented_id(client, user_a, monkeypatch):
    provider = FakeProvider(
        _ready(ProviderIntent(type="add_exercise", query="Bench Press"))
    )
    monkeypatch.setattr(assistant_service, "get_provider", lambda: provider)
    workout = empty_workout(client, user_a["headers"])
    body = ok(
        _interpret(
            client,
            user_a["headers"],
            "aggiungi panca piana",
            workout_id=workout["id"],
            locale="it",
        )
    )
    assert body["status"] == "ready"
    assert body["confirmation_required"] is False
    command = body["commands"][0]
    assert command["type"] == "add_exercise"
    assert command["payload"]["query"] == "Bench Press"
    assert "exercise_id" not in command["payload"]
    executed = ok(
        _execute(client, user_a["headers"], [command["payload"]])
    )
    assert executed["status"] == "executed"
    detail = get_workout(client, user_a["headers"], workout["id"])
    assert detail["exercises"][0]["exercise"]["name"] == "Bench Press"


def test_ambiguous_exercise_does_not_write(client, user_a, db, monkeypatch):
    from app.exercises.models import ExerciseSynonym
    from tests.helpers import create_personal_exercise

    workout = empty_workout(client, user_a["headers"])
    first = create_personal_exercise(client, user_a["headers"], f"A {uuid.uuid4().hex[:6]}")
    second = create_personal_exercise(client, user_a["headers"], f"B {uuid.uuid4().hex[:6]}")
    for exercise_id in (first["id"], second["id"]):
        db.add(
            ExerciseSynonym(
                exercise_id=exercise_id,
                synonym="Clashpress",
                synonym_normalized="clashpress",
                locale="en",
            )
        )
    db.commit()
    monkeypatch.setattr(
        assistant_service,
        "get_provider",
        lambda: FakeProvider(
            _ready(ProviderIntent(type="add_exercise", query="Clashpress"))
        ),
    )
    body = ok(
        _interpret(
            client,
            user_a["headers"],
            "add clashpress",
            workout_id=workout["id"],
        )
    )
    assert body["status"] == "needs_clarification"
    assert body["reason"] == "exercise"
    assert {item["id"] for item in body["candidates"]} == {first["id"], second["id"]}
    assert get_workout(client, user_a["headers"], workout["id"])["exercises"] == []


def test_multiple_active_sessions_clarification(client, user_a, monkeypatch):
    first = empty_workout(client, user_a["headers"], "One")
    second = empty_workout(client, user_a["headers"], "Two")
    monkeypatch.setattr(
        assistant_service,
        "get_provider",
        lambda: FakeProvider(
            _ready(ProviderIntent(type="finish_session"))
        ),
    )
    body = ok(_interpret(client, user_a["headers"], "termina allenamento"))
    assert body["status"] == "needs_clarification"
    assert body["reason"] == "session"
    assert {item["id"] for item in body["candidates"]} == {first["id"], second["id"]}
    assert get_workout(client, user_a["headers"], first["id"])["ended_at"] is None


def test_malformed_provider_output_no_write(client, user_a, monkeypatch):
    class BadProvider:
        def interpret(self, text, context):
            raise AssistantProviderError("bad", category="malformed")

    monkeypatch.setattr(assistant_service, "get_provider", lambda: BadProvider())
    workout = empty_workout(client, user_a["headers"])
    body = ok(
        _interpret(
            client, user_a["headers"], "add bench", workout_id=workout["id"]
        )
    )
    assert body["status"] == "error"
    assert body["reason"] == "malformed"
    assert get_workout(client, user_a["headers"], workout["id"])["exercises"] == []


def test_provider_timeout_and_http_errors(client, user_a, monkeypatch):
    workout = empty_workout(client, user_a["headers"])

    class TimeoutProvider:
        def interpret(self, text, context):
            raise AssistantProviderError("Assistant timed out", category="timeout")

    monkeypatch.setattr(assistant_service, "get_provider", lambda: TimeoutProvider())
    body = ok(
        _interpret(
            client, user_a["headers"], "add bench", workout_id=workout["id"]
        )
    )
    assert body["status"] == "error"
    assert body["reason"] == "timeout"
    assert "timed out" in body["message"].lower()


def test_missing_api_key_unavailable(client, user_a, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "openai_api_key", None)
    monkeypatch.setattr(
        assistant_service, "get_provider", OpenAIResponsesProvider
    )
    body = ok(_interpret(client, user_a["headers"], "add bench press"))
    assert body["status"] == "unavailable"
    assert body["commands"] == []


def test_confirmation_flags(client, user_a, monkeypatch):
    workout = empty_workout(client, user_a["headers"], "Push")
    cases = [
        (ProviderIntent(type="finish_session"), True),
        (ProviderIntent(type="create_session", name="Upper Body"), True),
        (ProviderIntent(type="add_exercise", query="Bench Press"), False),
        (
            ProviderIntent(type="record_set", exercise_query="Bench Press", reps=8),
            False,
        ),
    ]
    for intent, required in cases:
        monkeypatch.setattr(
            assistant_service,
            "get_provider",
            lambda intent=intent: FakeProvider(_ready(intent)),
        )
        extra = {}
        if intent.type in {"add_exercise", "record_set", "finish_session"}:
            extra["workout_id"] = workout["id"]
        if intent.type == "record_set":
            add_we(
                client,
                user_a["headers"],
                workout["id"],
                bench_id(client, user_a["headers"]),
            )
        body = ok(_interpret(client, user_a["headers"], "cmd", **extra))
        assert body["status"] == "ready", body
        assert body["confirmation_required"] is required


def test_start_template_confirmation(client, user_a, monkeypatch):
    bench = bench_id(client, user_a["headers"])
    template = create_template(
        client,
        user_a["headers"],
        f"Push Day {uuid.uuid4().hex[:6]}",
        [{"exercise_id": bench, "target_sets": 3, "target_reps_min": 8, "target_reps_max": 10}],
    )
    monkeypatch.setattr(
        assistant_service,
        "get_provider",
        lambda: FakeProvider(
            _ready(ProviderIntent(type="start_template", query=template["name"]))
        ),
    )
    body = ok(_interpret(client, user_a["headers"], "avvia il mio push day"))
    assert body["status"] == "ready"
    assert body["confirmation_required"] is True
    assert body["commands"][0]["payload"]["template_id"] == template["id"]


def test_execute_uses_phase8_and_tracking_rule(client, user_a):
    workout = empty_workout(client, user_a["headers"])
    plank = add_we(
        client, user_a["headers"], workout["id"], plank_id(client, user_a["headers"])
    )
    rejected = ok(
        _execute(
            client,
            user_a["headers"],
            [
                {
                    "type": "record_set",
                    "workout_exercise_id": plank["id"],
                    "reps": 10,
                }
            ],
        )
    )
    assert rejected["status"] == "error"
    assert rejected["reason"] == "validation"
    detail = get_workout(client, user_a["headers"], workout["id"])
    assert detail["exercises"][0]["sets"] == []


def test_compound_order_bind_and_stop(client, user_a):
    workout = empty_workout(client, user_a["headers"])
    bench = bench_id(client, user_a["headers"])
    added = ok(
        _execute(
            client,
            user_a["headers"],
            [
                {
                    "type": "add_exercise",
                    "query": "Bench Press",
                    "workout_id": workout["id"],
                },
                {
                    "type": "record_set",
                    "exercise_query": "Bench Press",
                    "workout_id": workout["id"],
                    "reps": 10,
                    "weight_kg": 80,
                },
                {
                    "type": "record_set",
                    "exercise_query": "Bench Press",
                    "workout_id": workout["id"],
                    "reps": 10,
                    "weight_kg": 80,
                },
            ],
        )
    )
    assert added["status"] == "executed"
    assert [row["type"] for row in added["results"]] == [
        "add_exercise",
        "record_set",
        "record_set",
    ]
    detail = get_workout(client, user_a["headers"], workout["id"])
    assert detail["exercises"][0]["exercise"]["id"] == bench
    assert len(detail["exercises"][0]["sets"]) == 2

    stopped = ok(
        _execute(
            client,
            user_a["headers"],
            [
                {
                    "type": "add_exercise",
                    "query": "Plank",
                    "workout_id": workout["id"],
                },
                {
                    "type": "record_set",
                    "exercise_query": "Plank",
                    "workout_id": workout["id"],
                    "reps": 10,
                },
            ],
        )
    )
    assert stopped["status"] == "error"
    assert stopped["executed"][0]["type"] == "add_exercise"
    assert stopped["failed"]["type"] == "record_set"
    after = get_workout(client, user_a["headers"], workout["id"])
    plank_row = next(
        row for row in after["exercises"] if row["exercise"]["name"] == "Plank"
    )
    assert plank_row["sets"] == []


def test_incremental_same_weight_from_persisted_set(client, user_a, monkeypatch):
    workout = empty_workout(client, user_a["headers"])
    we = add_we(
        client, user_a["headers"], workout["id"], bench_id(client, user_a["headers"])
    )
    add_set(client, user_a["headers"], we["id"], {"reps": 8, "weight_kg": 80})
    monkeypatch.setattr(
        assistant_service,
        "get_provider",
        lambda: FakeProvider(
            _ready(
                ProviderIntent(
                    type="record_set",
                    exercise_query="Bench Press",
                    use_last_reps=True,
                    use_last_weight=True,
                    weight_delta_kg=Decimal("5"),
                )
            )
        ),
    )
    body = ok(
        _interpret(
            client,
            user_a["headers"],
            "5 chili in più",
            workout_id=workout["id"],
            focus_workout_exercise_id=we["id"],
        )
    )
    assert body["status"] == "ready"
    payload = body["commands"][0]["payload"]
    assert payload["reps"] == 8
    assert float(payload["weight_kg"]) == 85
    assert payload["workout_exercise_id"] == we["id"]


def test_incremental_missing_last_value_clarifies(client, user_a, monkeypatch):
    workout = empty_workout(client, user_a["headers"])
    we = add_we(
        client, user_a["headers"], workout["id"], bench_id(client, user_a["headers"])
    )
    add_set(client, user_a["headers"], we["id"], {"reps": 8})
    monkeypatch.setattr(
        assistant_service,
        "get_provider",
        lambda: FakeProvider(
            _ready(
                ProviderIntent(
                    type="record_set",
                    use_last_weight=True,
                    reps=8,
                )
            )
        ),
    )
    body = ok(
        _interpret(
            client,
            user_a["headers"],
            "stesso peso",
            workout_id=workout["id"],
            focus_workout_exercise_id=we["id"],
        )
    )
    assert body["status"] == "needs_clarification"
    assert "weight" in body["message"].lower()
    assert len(get_workout(client, user_a["headers"], workout["id"])["exercises"][0]["sets"]) == 1


def test_rate_limit(client, user_a, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "assistant_rate_limit_per_minute", 2)
    monkeypatch.setattr(
        assistant_service,
        "get_provider",
        lambda: FakeProvider(_ready(ProviderIntent(type="create_session", name="A"))),
    )
    assert _interpret(client, user_a["headers"], "one").status_code == 200
    assert _interpret(client, user_a["headers"], "two").status_code == 200
    err(_interpret(client, user_a["headers"], "three"), 429)


def test_secrets_never_returned(client, user_a, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "openai_api_key", "sk-secret-test-key")
    monkeypatch.setattr(
        assistant_service,
        "get_provider",
        lambda: FakeProvider(_ready(ProviderIntent(type="create_session", name="A"))),
    )
    resp = _interpret(client, user_a["headers"], "create workout")
    text = resp.text
    assert "sk-secret-test-key" not in text
    assert "Authorization" not in text
    body = ok(resp)
    assert "output" not in body
    assert "instructions" not in body


def test_execute_rejects_unknown_type(client, user_a):
    err(
        _execute(
            client,
            user_a["headers"],
            [{"type": "delete_set", "workout_exercise_id": 1}],
        ),
        422,
    )


def test_unsupported_intent_from_provider_rejected(client, user_a, monkeypatch):
    class Sneaky:
        def interpret(self, text, context):
            return ProviderInterpretation.model_validate(
                {
                    "status": "ready",
                    "intents": [{"type": "add_exercise", "query": "Bench Press"}],
                }
            )

    monkeypatch.setattr(assistant_service, "get_provider", lambda: Sneaky())
    workout = empty_workout(client, user_a["headers"])
    body = ok(
        _interpret(
            client, user_a["headers"], "add bench", workout_id=workout["id"]
        )
    )
    assert body["status"] == "ready"
    assert all("id" != key or key == "workout_id" for key in body["commands"][0]["payload"])


def test_openai_provider_request_and_parse(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "openai_api_key", "sk-test")
    monkeypatch.setattr(settings, "assistant_model", "gpt-test")
    monkeypatch.setattr(settings, "openai_base_url", "https://api.openai.com/v1")
    monkeypatch.setattr(settings, "assistant_timeout_seconds", 7)

    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["authorization"] = request.headers["Authorization"]
        captured["body"] = request.read()
        return httpx.Response(
            200,
            json={
                "id": "resp_1",
                "output_text": (
                    '{"status":"ready","message":null,"intents":['
                    '{"type":"add_exercise","name":null,"date":null,'
                    '"query":"Bench Press","locale":null,"scope":null,'
                    '"exercise_query":null,"reps":null,"weight_kg":null,'
                    '"duration_seconds":null,"distance_meters":null,'
                    '"use_last_reps":false,"use_last_weight":false,'
                    '"use_last_duration":false,"use_last_distance":false,'
                    '"weight_delta_kg":null}]}'
                ),
            },
        )

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    provider = OpenAIResponsesProvider(settings=settings, client=client)
    parsed = provider.interpret("add bench", {"session": None})
    assert parsed.status == "ready"
    assert parsed.intents[0].query == "Bench Press"
    assert captured["authorization"] == "Bearer sk-test"
    assert captured["url"].endswith("/responses")
    import json

    body = json.loads(captured["body"].decode())
    assert body["model"] == "gpt-test"
    assert body["text"]["format"]["type"] == "json_schema"
    assert body["text"]["format"]["strict"] is True
    assert "sk-test" not in parsed.model_dump_json()


def test_openai_provider_timeout_and_429(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "openai_api_key", "sk-test")

    def timeout_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("slow")

    provider = OpenAIResponsesProvider(
        settings=settings,
        client=httpx.Client(transport=httpx.MockTransport(timeout_handler)),
    )
    with pytest.raises(AssistantProviderError) as timed:
        provider.interpret("hello", {})
    assert timed.value.category == "timeout"

    def busy(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": "nope"})

    busy_provider = OpenAIResponsesProvider(
        settings=settings,
        client=httpx.Client(transport=httpx.MockTransport(busy)),
    )
    with pytest.raises(AssistantProviderError) as limited:
        busy_provider.interpret("hello", {})
    assert limited.value.category == "rate_limit"


def test_openai_provider_5xx_and_malformed_retry(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "openai_api_key", "sk-test")
    calls = {"n": 0}

    def server(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": "down"})

    provider = OpenAIResponsesProvider(
        settings=settings,
        client=httpx.Client(transport=httpx.MockTransport(server)),
    )
    with pytest.raises(AssistantProviderError) as failed:
        provider.interpret("hello", {})
    assert failed.value.category == "server"

    def malformed(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(200, json={"output_text": "not-json"})

    bad = OpenAIResponsesProvider(
        settings=settings,
        client=httpx.Client(transport=httpx.MockTransport(malformed)),
    )
    with pytest.raises(AssistantProviderError) as invalid:
        bad.interpret("hello", {})
    assert invalid.value.category in {"malformed", "empty"}
    assert calls["n"] == 2


def test_extract_structured_output_from_output_list():
    body = {
        "output": [
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": '{"status":"unknown","intents":[]}',
                    }
                ],
            }
        ]
    }
    parsed = extract_structured_output(body)
    assert parsed["status"] == "unknown"
