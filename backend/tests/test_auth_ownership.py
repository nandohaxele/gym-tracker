"""Auth required + cross-user 404 (no existence leak)."""

from tests.helpers import (
    add_set,
    add_we,
    bench_id,
    create_template,
    empty_workout,
    err,
    ok,
)


def test_protected_routes_require_auth(client):
    for method, path in (
        ("get", "/api/exercises"),
        ("get", "/api/workouts"),
        ("get", "/api/templates"),
        ("get", "/api/auth/me"),
        ("get", "/api/exercises/last-weights"),
    ):
        resp = getattr(client, method)(path)
        err(resp, 401)


def test_foreign_workout_we_set_are_404(client, user_a, user_b):
    workout = empty_workout(client, user_a["headers"])
    we = add_we(client, user_a["headers"], workout["id"], bench_id(client, user_a["headers"]))
    recorded = add_set(client, user_a["headers"], we["id"], {"reps": 8, "weight_kg": 60})

    err(client.get(f"/api/workouts/{workout['id']}", headers=user_b["headers"]), 404)
    err(
        client.patch(
            f"/api/workouts/{workout['id']}",
            headers=user_b["headers"],
            json={"name": "Hijack"},
        ),
        404,
    )
    err(
        client.post(
            f"/api/workouts/{workout['id']}/complete",
            headers=user_b["headers"],
        ),
        404,
    )
    err(
        client.delete(
            f"/api/workout-exercises/{we['id']}",
            headers=user_b["headers"],
        ),
        404,
    )
    err(
        client.patch(
            f"/api/sets/{recorded['id']}",
            headers=user_b["headers"],
            json={"reps": 99},
        ),
        404,
    )
    err(client.delete(f"/api/sets/{recorded['id']}", headers=user_b["headers"]), 404)
    missing = err(client.get("/api/workouts/999999", headers=user_b["headers"]), 404)
    foreign = err(
        client.get(f"/api/workouts/{workout['id']}", headers=user_b["headers"]), 404
    )
    assert missing["error"] == foreign["error"]


def test_foreign_personal_template_404_global_readable(client, user_a, user_b, db):
    from app.exercises.normalization import normalize_name
    from app.templates.models import Template, TemplateExercise

    personal = create_template(
        client,
        user_a["headers"],
        "A-only plan",
        [
            {
                "exercise_id": bench_id(client, user_a["headers"]),
                "target_sets": 3,
                "target_reps_min": 8,
                "target_reps_max": 8,
            }
        ],
    )
    err(client.get(f"/api/templates/{personal['id']}", headers=user_b["headers"]), 404)
    err(
        client.delete(f"/api/templates/{personal['id']}", headers=user_b["headers"]),
        404,
    )

    global_row = Template(
        user_id=None,
        name="Shared Global",
        name_normalized=normalize_name("Shared Global"),
    )
    global_row.exercises.append(
        TemplateExercise(
            exercise_id=bench_id(client, user_a["headers"]),
            order_index=0,
            target_sets=2,
            target_reps_min=5,
            target_reps_max=5,
        )
    )
    db.add(global_row)
    db.commit()
    db.refresh(global_row)

    visible = ok(client.get(f"/api/templates/{global_row.id}", headers=user_b["headers"]))
    assert visible["is_global"] is True
    err(
        client.patch(
            f"/api/templates/{global_row.id}",
            headers=user_b["headers"],
            json={"name": "Nope"},
        ),
        422,
    )
