"""Primary-metric validation, optional weight, RPE/RIR, historical plank shape."""

import uuid

from tests.helpers import (
    add_set,
    add_we,
    bench_id,
    create_personal_exercise,
    empty_workout,
    err,
    get_workout,
    ok,
    plank_id,
)


def _we(client, headers, exercise_id: int):
    workout = empty_workout(client, headers)
    return add_we(client, headers, workout["id"], exercise_id)


def test_reps_primary_requires_reps(client, user_a):
    we = _we(client, user_a["headers"], bench_id(client, user_a["headers"]))
    err(
        client.post(
            f"/api/workout-exercises/{we['id']}/sets",
            headers=user_a["headers"],
            json={"weight_kg": 40},
        ),
        422,
    )
    ok(
        client.post(
            f"/api/workout-exercises/{we['id']}/sets",
            headers=user_a["headers"],
            json={"reps": 8, "weight_kg": 40},
        ),
        201,
    )


def test_duration_and_distance_primaries(client, user_a):
    we = _we(client, user_a["headers"], plank_id(client, user_a["headers"]))
    err(
        client.post(
            f"/api/workout-exercises/{we['id']}/sets",
            headers=user_a["headers"],
            json={"reps": 200},
        ),
        422,
    )
    err(
        client.post(
            f"/api/workout-exercises/{we['id']}/sets",
            headers=user_a["headers"],
            json={"rpe": 7, "rir": 2},
        ),
        422,
    )
    ok(
        client.post(
            f"/api/workout-exercises/{we['id']}/sets",
            headers=user_a["headers"],
            json={"duration_seconds": 45, "rpe": 7, "rir": 2, "set_type": "warmup"},
        ),
        201,
    )

    distance = create_personal_exercise(
        client, user_a["headers"], f"Row {uuid.uuid4().hex[:6]}", "distance", ["reps"]
    )
    dwe = _we(client, user_a["headers"], distance["id"])
    err(
        client.post(
            f"/api/workout-exercises/{dwe['id']}/sets",
            headers=user_a["headers"],
            json={"reps": 10},
        ),
        422,
    )
    ok(
        client.post(
            f"/api/workout-exercises/{dwe['id']}/sets",
            headers=user_a["headers"],
            json={"distance_meters": 500, "reps": 1},
        ),
        201,
    )


def test_weight_zero_distinct_and_negative_rejected(client, user_a):
    we = _we(client, user_a["headers"], bench_id(client, user_a["headers"]))
    zero = add_set(client, user_a["headers"], we["id"], {"reps": 10, "weight_kg": 0})
    assert zero["weight_kg"] == 0
    missing = add_set(client, user_a["headers"], we["id"], {"reps": 10})
    assert missing["weight_kg"] is None
    err(
        client.post(
            f"/api/workout-exercises/{we['id']}/sets",
            headers=user_a["headers"],
            json={"reps": 8, "weight_kg": -1},
        ),
        422,
    )


def test_rpe_rir_set_type_validation(client, user_a):
    we = _we(client, user_a["headers"], bench_id(client, user_a["headers"]))
    err(
        client.post(
            f"/api/workout-exercises/{we['id']}/sets",
            headers=user_a["headers"],
            json={"reps": 8, "rpe": 7.2},
        ),
        422,
    )
    err(
        client.post(
            f"/api/workout-exercises/{we['id']}/sets",
            headers=user_a["headers"],
            json={"reps": 8, "rir": 6},
        ),
        422,
    )
    err(
        client.post(
            f"/api/workout-exercises/{we['id']}/sets",
            headers=user_a["headers"],
            json={"reps": 8, "set_type": "cluster"},
        ),
        422,
    )
    ok(
        client.post(
            f"/api/workout-exercises/{we['id']}/sets",
            headers=user_a["headers"],
            json={"reps": 8, "rpe": 7.5, "rir": 5, "set_type": "dropset"},
        ),
        201,
    )


def test_historical_plank_shape_readable_without_duration(client, user_a, db):
    from app.workouts.models import Set

    workout = empty_workout(client, user_a["headers"], "Leg day clone")
    we = add_we(client, user_a["headers"], workout["id"], plank_id(client, user_a["headers"]))
    row = Set(
        workout_exercise_id=we["id"],
        reps=200,
        weight_kg=96,
        duration_seconds=None,
        order_index=0,
        set_type="working",
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    detail = get_workout(client, user_a["headers"], workout["id"])
    recorded = detail["exercises"][0]["sets"][0]
    assert recorded["id"] == row.id
    assert recorded["reps"] == 200
    assert recorded["weight_kg"] == 96
    assert recorded["duration_seconds"] is None
    patched = ok(
        client.patch(
            f"/api/sets/{row.id}",
            headers=user_a["headers"],
            json={"weight_kg": 90},
        )
    )
    assert patched["duration_seconds"] is None
    assert patched["weight_kg"] == 90
    err(
        client.patch(
            f"/api/sets/{row.id}",
            headers=user_a["headers"],
            json={"duration_seconds": None},
        ),
        422,
    )
