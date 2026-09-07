"""Exercise ownership, tracking freeze, archive cleanup."""

import uuid

from tests.helpers import (
    add_set,
    add_we,
    create_personal_exercise,
    create_template,
    empty_workout,
    err,
    exercise_named,
    get_workout,
    ok,
    plank_id,
)


def test_globals_and_personal_isolation(client, user_a, user_b):
    globals_a = {item["name"] for item in ok(client.get("/api/exercises", headers=user_a["headers"])) if item["is_global"]}
    globals_b = {item["name"] for item in ok(client.get("/api/exercises", headers=user_b["headers"])) if item["is_global"]}
    assert "Bench Press" in globals_a
    assert globals_a == globals_b

    name = f"Cable crunch {uuid.uuid4().hex[:6]}"
    mine = create_personal_exercise(client, user_a["headers"], name)
    assert mine["is_global"] is False
    listed_a = {item["id"] for item in ok(client.get("/api/exercises", headers=user_a["headers"]))}
    listed_b = {item["id"] for item in ok(client.get("/api/exercises", headers=user_b["headers"]))}
    assert mine["id"] in listed_a
    assert mine["id"] not in listed_b


def test_personal_name_uniqueness_and_global_reuse(client, user_a, user_b):
    create_personal_exercise(client, user_a["headers"], "My Press")
    err(
        client.post(
            "/api/exercises",
            headers=user_a["headers"],
            json={"name": "  my   press ", "primary_tracking_type": "reps"},
        ),
        409,
    )
    ok(
        client.post(
            "/api/exercises",
            headers=user_b["headers"],
            json={"name": "My Press", "primary_tracking_type": "reps"},
        ),
        201,
    )
    ok(
        client.post(
            "/api/exercises",
            headers=user_a["headers"],
            json={"name": "Bench Press", "primary_tracking_type": "reps"},
        ),
        201,
    )


def test_plank_primary_duration_and_exactly_one_primary(client, user_a):
    plank = exercise_named(client, user_a["headers"], "Plank")
    assert plank["primary_tracking_type"] == "duration"
    assert plank["secondary_tracking_types"] == []
    for item in ok(client.get("/api/exercises", headers=user_a["headers"])):
        assert item["primary_tracking_type"] in {"reps", "duration", "distance"}


def test_tracking_freeze_after_first_set(client, user_a):
    ex = create_personal_exercise(client, user_a["headers"], f"Hold {uuid.uuid4().hex[:6]}", "reps")
    ok(
        client.patch(
            f"/api/exercises/{ex['id']}",
            headers=user_a["headers"],
            json={"primary_tracking_type": "duration"},
        )
    )
    workout = empty_workout(client, user_a["headers"], "Freeze")
    we = add_we(client, user_a["headers"], workout["id"], ex["id"])
    add_set(client, user_a["headers"], we["id"], {"duration_seconds": 30})
    err(
        client.patch(
            f"/api/exercises/{ex['id']}",
            headers=user_a["headers"],
            json={"primary_tracking_type": "reps"},
        ),
        422,
    )
    ok(
        client.patch(
            f"/api/exercises/{ex['id']}",
            headers=user_a["headers"],
            json={"primary_tracking_type": "duration"},
        )
    )


def test_archive_hides_strips_templates_keeps_history(client, user_a):
    name = f"Archived press {uuid.uuid4().hex[:6]}"
    ex = create_personal_exercise(client, user_a["headers"], name)
    template = create_template(
        client,
        user_a["headers"],
        f"Uses {name}",
        [{"exercise_id": ex["id"], "target_sets": 2, "target_reps_min": 8, "target_reps_max": 10}],
    )
    workout = empty_workout(client, user_a["headers"], "History")
    we = add_we(client, user_a["headers"], workout["id"], ex["id"])
    add_set(client, user_a["headers"], we["id"], {"reps": 8, "weight_kg": 20})

    archived = ok(client.post(f"/api/exercises/{ex['id']}/archive", headers=user_a["headers"]))
    assert archived["is_active"] is False
    names = {item["name"] for item in ok(client.get("/api/exercises", headers=user_a["headers"]))}
    assert name not in names

    other = empty_workout(client, user_a["headers"], "New")
    err(
        client.post(
            f"/api/workouts/{other['id']}/exercises",
            headers=user_a["headers"],
            json={"exercise_id": ex["id"]},
        ),
        422,
    )

    history = get_workout(client, user_a["headers"], workout["id"])
    assert history["exercises"][0]["exercise"]["name"] == name
    assert history["exercises"][0]["exercise"]["is_active"] is False
    assert history["exercises"][0]["sets"][0]["reps"] == 8

    refreshed = ok(client.get(f"/api/templates/{template['id']}", headers=user_a["headers"]))
    assert refreshed["exercises"] == []
    assert refreshed["name"] == template["name"]
