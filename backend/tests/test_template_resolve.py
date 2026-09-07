"""Exact Template resolution HTTP contract."""

import uuid

from sqlalchemy import text

from app.exercises.normalization import normalize_name
from app.templates.models import Template
from tests.helpers import bench_id, create_template, err, ok


def _resolve(client, headers, query, scope=None):
    payload = {"query": query}
    if scope is not None:
        payload["scope"] = scope
    return ok(client.post("/api/templates/resolve", headers=headers, json=payload))


def _insert_global(db, name: str) -> Template:
    row = Template(
        user_id=None,
        name=name,
        name_normalized=normalize_name(name),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def test_personal_wins_over_global_with_scope_any(client, user_a, db):
    name = f"Push {uuid.uuid4().hex[:6]}"
    _insert_global(db, name)
    personal = create_template(client, user_a["headers"], name, [])
    body = _resolve(client, user_a["headers"], f"  {name} ")
    assert body["status"] == "resolved"
    assert body["scope"] == "any"
    assert body["level"] == "personal"
    assert body["template"]["id"] == personal["id"]
    assert body["template"]["is_global"] is False
    assert body["candidates"] == []


def test_scope_personal_and_global(client, user_a, db):
    name = f"Push Day {uuid.uuid4().hex[:6]}"
    global_row = _insert_global(db, name)
    personal = create_template(client, user_a["headers"], name, [])

    only_personal = _resolve(client, user_a["headers"], name, scope="personal")
    assert only_personal["status"] == "resolved"
    assert only_personal["scope"] == "personal"
    assert only_personal["template"]["id"] == personal["id"]

    only_global = _resolve(client, user_a["headers"], name, scope="global")
    assert only_global["status"] == "resolved"
    assert only_global["scope"] == "global"
    assert only_global["level"] == "global"
    assert only_global["template"]["id"] == global_row.id


def test_not_found_and_exact_only(client, user_a):
    name = f"Heavy Push Day {uuid.uuid4().hex[:6]}"
    create_template(client, user_a["headers"], name, [])
    missing = _resolve(client, user_a["headers"], "heavy push")
    assert missing["status"] == "not_found"
    assert missing["template"] is None
    assert missing["candidates"] == []
    assert missing["level"] is None


def test_same_level_ambiguity_if_constructed(client, user_a, db):
    db.execute(text("DROP INDEX IF EXISTS uq_templates_personal_name_normalized"))
    db.commit()
    first = Template(
        user_id=user_a["user_id"],
        name="Clash A",
        name_normalized="clash",
    )
    second = Template(
        user_id=user_a["user_id"],
        name="Clash B",
        name_normalized="clash",
    )
    db.add_all([first, second])
    db.commit()
    db.refresh(first)
    db.refresh(second)
    try:
        body = _resolve(client, user_a["headers"], "clash")
        assert body["status"] == "ambiguous"
        assert body["level"] == "personal"
        assert body["template"] is None
        assert {item["id"] for item in body["candidates"]} == {first.id, second.id}
    finally:
        db.delete(first)
        db.delete(second)
        db.commit()
        db.execute(
            text(
                "CREATE UNIQUE INDEX uq_templates_personal_name_normalized "
                "ON templates (user_id, name_normalized) WHERE user_id IS NOT NULL"
            )
        )
        db.commit()


def test_foreign_personal_invisible_global_readable(client, user_a, user_b, db):
    personal = create_template(client, user_a["headers"], "A-only plan", [])
    global_row = _insert_global(db, "Shared Plan")

    hidden = _resolve(client, user_b["headers"], "A-only plan")
    assert hidden["status"] == "not_found"
    assert str(personal["id"]) not in str(hidden)

    visible = _resolve(client, user_b["headers"], "Shared Plan")
    assert visible["status"] == "resolved"
    assert visible["template"]["id"] == global_row.id
    assert visible["template"]["is_global"] is True


def test_empty_query_invalid_scope_and_auth(client, user_a):
    err(
        client.post(
            "/api/templates/resolve",
            headers=user_a["headers"],
            json={"query": "  "},
        ),
        422,
    )
    err(
        client.post(
            "/api/templates/resolve",
            headers=user_a["headers"],
            json={"query": "Push", "scope": "both"},
        ),
        422,
    )
    err(client.post("/api/templates/resolve", json={"query": "Push"}), 401)


def test_resolver_outcomes_are_http_200(client, user_a):
    create_template(
        client,
        user_a["headers"],
        f"Named {uuid.uuid4().hex[:6]}",
        [{"exercise_id": bench_id(client, user_a["headers"]), "target_sets": 1, "target_reps_min": 5, "target_reps_max": 5}],
    )
    for query in ("Named missing", "no-such-template"):
        resp = client.post(
            "/api/templates/resolve",
            headers=user_a["headers"],
            json={"query": query},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True
