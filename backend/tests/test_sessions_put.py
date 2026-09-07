"""Session clocks, complete idempotency, PATCH scalars, legacy PUT."""

from datetime import date

from app.core.utc import date_midnight_utc, serialize_utc
from tests.helpers import (
    add_set,
    add_we,
    bench_id,
    create_template,
    empty_workout,
    err,
    get_workout,
    ok,
)


def test_empty_create_is_active_utc_and_complete_idempotent(client, user_a):
    workout = empty_workout(client, user_a["headers"], "Live")
    assert workout["ended_at"] is None
    assert workout["started_at"].endswith("Z")
    assert workout["created_at"].endswith("Z") or "+00:00" in workout["created_at"]

    first = ok(client.post(f"/api/workouts/{workout['id']}/complete", headers=user_a["headers"]))
    assert first["ended_at"] is not None
    assert first["ended_at"].endswith("Z")
    second = ok(client.post(f"/api/workouts/{workout['id']}/complete", headers=user_a["headers"]))
    assert second["ended_at"] == first["ended_at"]


def test_retrospective_create_uses_midnight_sentinel(client, user_a):
    payload = {
        "name": "Logged later",
        "date": "2026-06-19",
        "exercises": [
            {
                "exercise_id": bench_id(client, user_a["headers"]),
                "sets": [{"reps": 8, "weight_kg": 60}],
            }
        ],
    }
    workout = ok(client.post("/api/workouts", headers=user_a["headers"], json=payload), 201)
    expected = serialize_utc(date_midnight_utc(date(2026, 6, 19)))
    assert workout["started_at"] == expected
    assert workout["ended_at"] == expected


def test_completed_session_stays_editable_clocks_untouched(client, user_a):
    workout = empty_workout(client, user_a["headers"])
    we = add_we(client, user_a["headers"], workout["id"], bench_id(client, user_a["headers"]))
    add_set(client, user_a["headers"], we["id"], {"reps": 8, "weight_kg": 40})
    completed = ok(client.post(f"/api/workouts/{workout['id']}/complete", headers=user_a["headers"]))
    ended = completed["ended_at"]
    started = completed["started_at"]

    patched = ok(
        client.patch(
            f"/api/workouts/{workout['id']}",
            headers=user_a["headers"],
            json={"name": "Corrected", "date": "2026-01-01"},
        )
    )
    assert patched["name"] == "Corrected"
    assert patched["date"] == "2026-01-01"
    assert patched["ended_at"] == ended
    assert patched["started_at"] == started
    assert len(patched["exercises"]) == 1

    extra = add_set(client, user_a["headers"], we["id"], {"reps": 6, "weight_kg": 42.5})
    after = get_workout(client, user_a["headers"], workout["id"])
    assert after["ended_at"] == ended
    assert extra["id"] in {row["id"] for row in after["exercises"][0]["sets"]}


def test_id_bearing_put_preserves_children_planned_and_provenance(client, user_a):
    bench = bench_id(client, user_a["headers"])
    template = ok(
        client.post(
            "/api/templates",
            headers=user_a["headers"],
            json={
                "name": "Put source",
                "exercises": [
                    {
                        "exercise_id": bench,
                        "target_sets": 3,
                        "target_reps_min": 8,
                        "target_reps_max": 10,
                    }
                ],
            },
        ),
        201,
    )
    started = ok(
        client.post(f"/api/templates/{template['id']}/start", headers=user_a["headers"]),
        201,
    )
    we = started["exercises"][0]
    first = add_set(client, user_a["headers"], we["id"], {"reps": 8, "weight_kg": 50})
    second = add_set(client, user_a["headers"], we["id"], {"reps": 8, "weight_kg": 52.5})

    updated = ok(
        client.put(
            f"/api/workouts/{started['id']}",
            headers=user_a["headers"],
            json={
                "name": "Still from template",
                "date": started["date"],
                "exercises": [
                    {
                        "id": we["id"],
                        "exercise_id": bench,
                        "sets": [
                            {"id": first["id"], "reps": 9, "weight_kg": 50},
                            {"id": second["id"], "reps": 8, "weight_kg": 52.5},
                        ],
                    }
                ],
            },
        )
    )
    assert updated["source_template_id"] == template["id"]
    assert updated["exercises"][0]["id"] == we["id"]
    assert updated["exercises"][0]["planned_sets"] == 3
    assert updated["exercises"][0]["planned_reps_min"] == 8
    assert [row["id"] for row in updated["exercises"][0]["sets"]] == [
        first["id"],
        second["id"],
    ]
    assert updated["exercises"][0]["sets"][0]["reps"] == 9
    source = ok(client.get(f"/api/templates/{template['id']}", headers=user_a["headers"]))
    assert source["exercises"][0]["target_sets"] == 3


def test_ambiguous_idless_put_rejects(client, user_a):
    bench = bench_id(client, user_a["headers"])
    workout = empty_workout(client, user_a["headers"])
    first = add_we(client, user_a["headers"], workout["id"], bench)
    second = add_we(client, user_a["headers"], workout["id"], bench)
    add_set(client, user_a["headers"], first["id"], {"reps": 8, "weight_kg": 40})
    add_set(client, user_a["headers"], second["id"], {"reps": 6, "weight_kg": 45})

    err(
        client.put(
            f"/api/workouts/{workout['id']}",
            headers=user_a["headers"],
            json={
                "name": "Guess",
                "exercises": [
                    {"exercise_id": bench, "sets": [{"reps": 8, "weight_kg": 40}]},
                    {"exercise_id": bench, "sets": [{"reps": 6, "weight_kg": 45}]},
                ],
            },
        ),
        422,
    )
    after = get_workout(client, user_a["headers"], workout["id"])
    assert {we["id"] for we in after["exercises"]} == {first["id"], second["id"]}
