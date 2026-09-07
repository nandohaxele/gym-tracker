"""GET /api/workouts/active — 0 / 1 / many, ownership, completed excluded."""

from tests.helpers import empty_workout, err, ok


def test_zero_one_and_many_active(client, user_a):
    assert ok(client.get("/api/workouts/active", headers=user_a["headers"])) == []

    first = empty_workout(client, user_a["headers"], "One")
    only = ok(client.get("/api/workouts/active", headers=user_a["headers"]))
    assert [row["id"] for row in only] == [first["id"]]
    assert only[0]["ended_at"] is None

    second = empty_workout(client, user_a["headers"], "Two")
    many = ok(client.get("/api/workouts/active", headers=user_a["headers"]))
    assert {row["id"] for row in many} == {first["id"], second["id"]}
    assert all(row["ended_at"] is None for row in many)


def test_completed_and_foreign_active_excluded(client, user_a, user_b):
    mine = empty_workout(client, user_a["headers"], "Mine")
    theirs = empty_workout(client, user_b["headers"], "Theirs")
    finished = empty_workout(client, user_a["headers"], "Done")
    ok(client.post(f"/api/workouts/{finished['id']}/complete", headers=user_a["headers"]))

    listed = ok(client.get("/api/workouts/active", headers=user_a["headers"]))
    ids = {row["id"] for row in listed}
    assert mine["id"] in ids
    assert finished["id"] not in ids
    assert theirs["id"] not in ids

    other = ok(client.get("/api/workouts/active", headers=user_b["headers"]))
    assert {row["id"] for row in other} == {theirs["id"]}


def test_active_route_is_not_parsed_as_workout_id(client, user_a):
    resp = client.get("/api/workouts/active", headers=user_a["headers"])
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert isinstance(body["data"], list)


def test_active_requires_auth(client):
    err(client.get("/api/workouts/active"), 401)
