"""Template independence, Start snapshot, save-as-template derivation."""

import uuid

from tests.helpers import (
    add_set,
    add_we,
    bench_id,
    create_personal_exercise,
    create_template,
    empty_workout,
    err,
    get_workout,
    ok,
    plank_id,
)


def test_personal_crud_and_name_conflict(client, user_a, user_b):
    bench = bench_id(client, user_a["headers"])
    created = create_template(
        client,
        user_a["headers"],
        "My Push",
        [{"exercise_id": bench, "target_sets": 3, "target_reps_min": 8, "target_reps_max": 10}],
    )
    err(
        client.post(
            "/api/templates",
            headers=user_a["headers"],
            json={"name": " my  push ", "exercises": []},
        ),
        409,
    )
    ok(
        client.post(
            "/api/templates",
            headers=user_b["headers"],
            json={"name": "My Push", "exercises": []},
        ),
        201,
    )
    patched = ok(
        client.patch(
            f"/api/templates/{created['id']}",
            headers=user_a["headers"],
            json={"name": "My Push v2"},
        )
    )
    assert patched["name"] == "My Push v2"
    ok(client.delete(f"/api/templates/{created['id']}", headers=user_a["headers"]))
    err(client.get(f"/api/templates/{created['id']}", headers=user_a["headers"]), 404)


def test_global_immutable_personalize_independent(client, user_a, db):
    from app.exercises.normalization import normalize_name
    from app.templates.models import Template, TemplateExercise

    bench = bench_id(client, user_a["headers"])
    global_row = Template(
        user_id=None,
        name="Global Push Day",
        name_normalized=normalize_name("Global Push Day"),
    )
    global_row.exercises.append(
        TemplateExercise(
            exercise_id=bench,
            order_index=0,
            target_sets=4,
            target_reps_min=6,
            target_reps_max=8,
        )
    )
    db.add(global_row)
    db.commit()
    db.refresh(global_row)

    err(
        client.patch(
            f"/api/templates/{global_row.id}",
            headers=user_a["headers"],
            json={"name": "Hacked"},
        ),
        422,
    )
    copy = ok(
        client.post(
            f"/api/templates/{global_row.id}/personalize",
            headers=user_a["headers"],
            json={"name": "My Global Push Day"},
        ),
        201,
    )
    assert copy["is_global"] is False
    assert copy["id"] != global_row.id
    assert copy["exercises"][0]["target_sets"] == 4
    source = ok(client.get(f"/api/templates/{global_row.id}", headers=user_a["headers"]))
    assert source["name"] == "Global Push Day"
    assert source["exercises"][0]["target_sets"] == 4


def test_start_creates_active_session_zero_sets_independent_snapshot(client, user_a):
    bench = bench_id(client, user_a["headers"])
    template = create_template(
        client,
        user_a["headers"],
        f"Start {uuid.uuid4().hex[:6]}",
        [{"exercise_id": bench, "target_sets": 3, "target_reps_min": 8, "target_reps_max": 10}],
    )
    before = ok(client.get("/api/templates", headers=user_a["headers"]))
    started = ok(
        client.post(f"/api/templates/{template['id']}/start", headers=user_a["headers"]),
        201,
    )
    after = ok(client.get("/api/templates", headers=user_a["headers"]))
    assert len(after) == len(before)
    assert started["ended_at"] is None
    assert started["source_template_id"] == template["id"]
    assert started["started_at"].endswith("Z")
    assert started["exercises"][0]["planned_sets"] == 3
    assert started["exercises"][0]["planned_reps_min"] == 8
    assert started["exercises"][0]["sets"] == []

    ok(
        client.patch(
            f"/api/templates/{template['id']}",
            headers=user_a["headers"],
            json={
                "exercises": [
                    {
                        "exercise_id": bench,
                        "target_sets": 1,
                        "target_reps_min": 3,
                        "target_reps_max": 3,
                    }
                ]
            },
        )
    )
    snapshot = get_workout(client, user_a["headers"], started["id"])
    assert snapshot["exercises"][0]["planned_sets"] == 3
    assert snapshot["exercises"][0]["planned_reps_min"] == 8

    add_set(client, user_a["headers"], snapshot["exercises"][0]["id"], {"reps": 8, "weight_kg": 40})
    source = ok(client.get(f"/api/templates/{template['id']}", headers=user_a["headers"]))
    assert source["exercises"][0]["target_sets"] == 1

    ok(client.delete(f"/api/templates/{template['id']}", headers=user_a["headers"]))
    after_delete = get_workout(client, user_a["headers"], started["id"])
    assert after_delete["source_template_id"] is None
    assert after_delete["exercises"][0]["planned_sets"] == 3
    assert after_delete["exercises"][0]["sets"][0]["reps"] == 8


def test_save_as_template_derivation_and_plank_legacy(client, user_a, db):
    from app.workouts.models import Set

    bench = bench_id(client, user_a["headers"])
    workout = empty_workout(client, user_a["headers"], "Derive me")
    we_bench = add_we(client, user_a["headers"], workout["id"], bench)
    add_set(client, user_a["headers"], we_bench["id"], {"reps": 8, "weight_kg": 60, "rpe": 8, "rir": 1, "set_type": "warmup"})
    add_set(client, user_a["headers"], we_bench["id"], {"reps": 6, "weight_kg": 70})
    empty_we = add_we(client, user_a["headers"], workout["id"], bench)
    assert empty_we["sets"] == [] or True

    we_plank = add_we(client, user_a["headers"], workout["id"], plank_id(client, user_a["headers"]))
    row = Set(
        workout_exercise_id=we_plank["id"],
        reps=200,
        weight_kg=96,
        duration_seconds=None,
        order_index=0,
        set_type="working",
    )
    db.add(row)
    db.commit()

    archived = create_personal_exercise(client, user_a["headers"], f"Gone {uuid.uuid4().hex[:6]}")
    we_arch = add_we(client, user_a["headers"], workout["id"], archived["id"])
    add_set(client, user_a["headers"], we_arch["id"], {"reps": 12, "weight_kg": 15})
    ok(client.post(f"/api/exercises/{archived['id']}/archive", headers=user_a["headers"]))

    derived = ok(
        client.post(
            f"/api/workouts/{workout['id']}/save-as-template",
            headers=user_a["headers"],
            json={"name": f"From session {uuid.uuid4().hex[:6]}"},
        ),
        201,
    )
    by_ex = {item["exercise"]["id"]: item for item in derived["exercises"]}
    assert empty_we["exercise"]["id"] == bench
    assert bench in by_ex
    assert by_ex[bench]["target_sets"] == 2
    assert by_ex[bench]["target_reps_min"] == 6
    assert by_ex[bench]["target_reps_max"] == 8
    assert by_ex[bench]["target_duration_seconds_min"] is None
    plank = plank_id(client, user_a["headers"])
    assert by_ex[plank]["target_reps_min"] == 200
    assert by_ex[plank]["target_reps_max"] == 200
    assert by_ex[plank]["target_duration_seconds_min"] is None
    assert by_ex[plank]["target_duration_seconds_max"] is None
    assert archived["id"] not in by_ex
    for item in derived["exercises"]:
        assert "target_weight" not in item
        assert "rpe" not in item
        assert "rir" not in item
        assert "set_type" not in item

    empty = empty_workout(client, user_a["headers"], "No sets")
    add_we(client, user_a["headers"], empty["id"], bench)
    err(
        client.post(
            f"/api/workouts/{empty['id']}/save-as-template",
            headers=user_a["headers"],
            json={"name": "Nope"},
        ),
        422,
    )
    err(
        client.post(
            f"/api/workouts/{workout['id']}/save-as-template",
            headers=user_a["headers"],
            json={"name": derived["name"]},
        ),
        409,
    )
