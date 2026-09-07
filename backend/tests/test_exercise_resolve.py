"""Exact Exercise resolution HTTP contract and security."""

import uuid

from app.exercises.models import ExerciseSynonym
from app.exercises.normalization import normalize_name
from tests.helpers import create_personal_exercise, err, exercise_named, ok


def _resolve(client, headers, query, locale=None, status=200):
    payload = {"query": query}
    if locale is not None:
        payload["locale"] = locale
    resp = client.post("/api/exercises/resolve", headers=headers, json=payload)
    return ok(resp, status)


def test_personal_exact_beats_global_exact(client, user_a):
    mine = create_personal_exercise(client, user_a["headers"], "Bench Press")
    body = _resolve(client, user_a["headers"], "  Bench   Press ")
    assert body["status"] == "resolved"
    assert body["level"] == "personal_name"
    assert body["normalized"] == "bench press"
    assert body["exercise"]["id"] == mine["id"]
    assert body["exercise"]["is_global"] is False
    assert body["candidates"] == []


def test_personal_synonym_beats_global_exact(client, user_a):
    mine = create_personal_exercise(
        client,
        user_a["headers"],
        f"Home bench {uuid.uuid4().hex[:6]}",
        synonyms=["Bench Press"],
    )
    body = _resolve(client, user_a["headers"], "Bench Press")
    assert body["status"] == "resolved"
    assert body["level"] == "personal_synonym"
    assert body["exercise"]["id"] == mine["id"]


def test_global_exact_beats_global_synonym(client, user_a):
    bench = exercise_named(client, user_a["headers"], "Bench Press")
    body = _resolve(client, user_a["headers"], "Bench Press")
    assert body["status"] == "resolved"
    assert body["level"] == "global_name"
    assert body["exercise"]["id"] == bench["id"]
    assert body["exercise"]["slug"] == "bench-press"

    synonym = _resolve(client, user_a["headers"], "Bench")
    assert synonym["status"] == "resolved"
    assert synonym["level"] == "global_synonym"
    assert synonym["exercise"]["id"] == bench["id"]


def test_personal_synonym_beats_global_synonym(client, user_a):
    mine = create_personal_exercise(
        client,
        user_a["headers"],
        f"Flat board {uuid.uuid4().hex[:6]}",
        synonyms=["Bench"],
    )
    body = _resolve(client, user_a["headers"], "Bench")
    assert body["status"] == "resolved"
    assert body["level"] == "personal_synonym"
    assert body["exercise"]["id"] == mine["id"]


def test_same_level_ambiguity_does_not_guess(client, user_a, db):
    first = create_personal_exercise(client, user_a["headers"], f"Press A {uuid.uuid4().hex[:6]}")
    second = create_personal_exercise(client, user_a["headers"], f"Press B {uuid.uuid4().hex[:6]}")
    for exercise_id in (first["id"], second["id"]):
        db.add(
            ExerciseSynonym(
                exercise_id=exercise_id,
                synonym="Press",
                synonym_normalized=normalize_name("Press"),
                locale="en",
            )
        )
    db.commit()

    body = _resolve(client, user_a["headers"], "press")
    assert body["status"] == "ambiguous"
    assert body["level"] == "personal_synonym"
    assert body["exercise"] is None
    ids = {item["id"] for item in body["candidates"]}
    assert ids == {first["id"], second["id"]}
    assert all(item["is_global"] is False for item in body["candidates"])


def test_candidate_dedupes_same_exercise_across_locales(client, user_a, db):
    mine = create_personal_exercise(client, user_a["headers"], f"Panca {uuid.uuid4().hex[:6]}")
    for locale in ("en", "it"):
        db.add(
            ExerciseSynonym(
                exercise_id=mine["id"],
                synonym="Panca piana",
                synonym_normalized=normalize_name("Panca piana"),
                locale=locale,
            )
        )
    db.commit()

    body = _resolve(client, user_a["headers"], "Panca piana")
    assert body["status"] == "resolved"
    assert body["exercise"]["id"] == mine["id"]
    assert body["candidates"] == []


def test_locale_filters_synonyms_only(client, user_a, db):
    mine = create_personal_exercise(client, user_a["headers"], f"Italian only {uuid.uuid4().hex[:6]}")
    db.add(
        ExerciseSynonym(
            exercise_id=mine["id"],
            synonym="Panca",
            synonym_normalized="panca",
            locale="it",
        )
    )
    db.commit()

    italian = _resolve(client, user_a["headers"], "Panca", locale="it")
    assert italian["status"] == "resolved"
    assert italian["locale"] == "it"
    assert italian["exercise"]["id"] == mine["id"]

    english = _resolve(client, user_a["headers"], "Panca", locale="en")
    assert english["status"] == "not_found"
    assert english["exercise"] is None
    assert english["candidates"] == []

    any_locale = _resolve(client, user_a["headers"], "Panca")
    assert any_locale["status"] == "resolved"
    assert any_locale["locale"] is None
    assert any_locale["exercise"]["id"] == mine["id"]


def test_locale_does_not_affect_exact_name(client, user_a):
    mine = create_personal_exercise(client, user_a["headers"], f"Cable fly {uuid.uuid4().hex[:6]}")
    body = _resolve(client, user_a["headers"], mine["name"], locale="it")
    assert body["status"] == "resolved"
    assert body["level"] == "personal_name"
    assert body["exercise"]["id"] == mine["id"]


def test_archived_personal_does_not_resolve_or_shadow(client, user_a):
    unique = f"Solo move {uuid.uuid4().hex[:6]}"
    archived = create_personal_exercise(client, user_a["headers"], unique)
    ok(client.post(f"/api/exercises/{archived['id']}/archive", headers=user_a["headers"]))
    missing = _resolve(client, user_a["headers"], unique)
    assert missing["status"] == "not_found"

    shadow = create_personal_exercise(client, user_a["headers"], "Bench Press")
    ok(client.post(f"/api/exercises/{shadow['id']}/archive", headers=user_a["headers"]))
    global_bench = exercise_named(client, user_a["headers"], "Bench Press")
    body = _resolve(client, user_a["headers"], "Bench Press")
    assert body["status"] == "resolved"
    assert body["level"] == "global_name"
    assert body["exercise"]["id"] == global_bench["id"]


def test_foreign_personal_never_leaks(client, user_a, user_b):
    secret_name = f"Secret press {uuid.uuid4().hex[:6]}"
    secret = create_personal_exercise(
        client, user_a["headers"], secret_name, synonyms=["Hidden alias"]
    )
    body = _resolve(client, user_b["headers"], secret_name)
    assert body["status"] == "not_found"
    assert body["exercise"] is None
    assert body["candidates"] == []
    alias = _resolve(client, user_b["headers"], "Hidden alias")
    assert alias["status"] == "not_found"
    assert alias["exercise"] is None
    assert alias["candidates"] == []
    assert body["exercise"] is None
    leaked = str(body.get("exercise")) + str(body["candidates"]) + str(alias["candidates"])
    assert str(secret["id"]) not in leaked


def test_exact_match_only_no_fuzzy(client, user_a):
    body = _resolve(client, user_a["headers"], "press")
    assert body["status"] == "not_found"


def test_empty_query_and_auth(client, user_a):
    err(
        client.post("/api/exercises/resolve", headers=user_a["headers"], json={"query": "   "}),
        422,
    )
    err(client.post("/api/exercises/resolve", json={"query": "Bench Press"}), 401)


def test_resolver_outcomes_are_http_200(client, user_a):
    for query in ("Bench Press", "definitely-missing-move"):
        resp = client.post(
            "/api/exercises/resolve",
            headers=user_a["headers"],
            json={"query": query},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True
