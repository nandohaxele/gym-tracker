"""GET /api/exercises/last-weights user scoping and selection rules."""

from tests.helpers import (
    add_set,
    add_we,
    bench_id,
    create_personal_exercise,
    empty_workout,
    ok,
)


def test_last_weights_user_scoped_exclude_and_zero(client, user_a, user_b):
    bench = bench_id(client, user_a["headers"])
    older = empty_workout(client, user_a["headers"], "Older")
    ok(
        client.patch(
            f"/api/workouts/{older['id']}",
            headers=user_a["headers"],
            json={"date": "2026-01-01"},
        )
    )
    we_old = add_we(client, user_a["headers"], older["id"], bench)
    add_set(client, user_a["headers"], we_old["id"], {"reps": 8, "weight_kg": 40})

    newer = empty_workout(client, user_a["headers"], "Newer")
    ok(
        client.patch(
            f"/api/workouts/{newer['id']}",
            headers=user_a["headers"],
            json={"date": "2026-08-01"},
        )
    )
    we_new = add_we(client, user_a["headers"], newer["id"], bench)
    add_set(client, user_a["headers"], we_new["id"], {"reps": 5})
    add_set(client, user_a["headers"], we_new["id"], {"reps": 5, "weight_kg": 0})

    other = empty_workout(client, user_b["headers"], "B")
    we_b = add_we(client, user_b["headers"], other["id"], bench)
    add_set(client, user_b["headers"], we_b["id"], {"reps": 3, "weight_kg": 200})

    latest = ok(
        client.get(
            f"/api/exercises/last-weights?ids={bench}",
            headers=user_a["headers"],
        )
    )
    assert latest == [{"exercise_id": bench, "weight_kg": 0}]

    excluded = ok(
        client.get(
            f"/api/exercises/last-weights?ids={bench}&exclude_workout_id={newer['id']}",
            headers=user_a["headers"],
        )
    )
    assert excluded == [{"exercise_id": bench, "weight_kg": 40}]

    leaked = ok(
        client.get(
            f"/api/exercises/last-weights?ids={bench}",
            headers=user_b["headers"],
        )
    )
    assert leaked == [{"exercise_id": bench, "weight_kg": 200}]


def test_last_weights_unknown_and_archived(client, user_a):
    unknown = ok(
        client.get("/api/exercises/last-weights?ids=999999", headers=user_a["headers"])
    )
    assert unknown == [{"exercise_id": 999999, "weight_kg": None}]

    personal = create_personal_exercise(client, user_a["headers"], "Temp load")
    workout = empty_workout(client, user_a["headers"])
    we = add_we(client, user_a["headers"], workout["id"], personal["id"])
    add_set(client, user_a["headers"], we["id"], {"reps": 10, "weight_kg": 12.5})
    ok(client.post(f"/api/exercises/{personal['id']}/archive", headers=user_a["headers"]))
    rows = ok(
        client.get(
            f"/api/exercises/last-weights?ids={personal['id']}",
            headers=user_a["headers"],
        )
    )
    assert rows == [{"exercise_id": personal["id"], "weight_kg": 12.5}]
