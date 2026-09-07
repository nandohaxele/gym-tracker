"""Small HTTP helpers for the Phase 7 regression suite."""

from __future__ import annotations

from typing import Any

PASSWORD = "password12"


def register_login(client, email: str, password: str = PASSWORD) -> dict[str, Any]:
    created = client.post(
        "/api/auth/register", json={"email": email, "password": password}
    )
    assert created.status_code == 201, created.text
    login = client.post("/api/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    token = login.json()["data"]["access_token"]
    return {
        "email": email,
        "headers": {"Authorization": f"Bearer {token}"},
        "user_id": created.json()["data"]["id"],
    }


def ok(resp, status: int = 200):
    assert resp.status_code == status, resp.text
    body = resp.json()
    assert body["success"] is True
    assert body["error"] is None
    return body["data"]


def err(resp, status: int):
    assert resp.status_code == status, resp.text
    body = resp.json()
    assert body["success"] is False
    assert body["data"] is None
    assert body["error"]
    return body


def catalog(client, headers) -> list[dict]:
    return ok(client.get("/api/exercises", headers=headers))


def exercise_named(client, headers, name: str) -> dict:
    match = next((item for item in catalog(client, headers) if item["name"] == name), None)
    assert match is not None, f"missing catalog exercise {name!r}"
    return match


def bench_id(client, headers) -> int:
    return exercise_named(client, headers, "Bench Press")["id"]


def plank_id(client, headers) -> int:
    return exercise_named(client, headers, "Plank")["id"]


def squat_id(client, headers) -> int:
    return exercise_named(client, headers, "Back Squat")["id"]


def create_personal_exercise(
    client,
    headers,
    name: str,
    primary: str = "reps",
    secondaries: list[str] | None = None,
    muscle_group: str | None = None,
):
    payload = {
        "name": name,
        "primary_tracking_type": primary,
        "secondary_tracking_types": secondaries or [],
    }
    if muscle_group is not None:
        payload["muscle_group"] = muscle_group
    return ok(client.post("/api/exercises", headers=headers, json=payload), 201)


def empty_workout(client, headers, name: str = "Session"):
    return ok(
        client.post(
            "/api/workouts",
            headers=headers,
            json={"name": name, "date": "2026-09-07"},
        ),
        201,
    )


def add_we(client, headers, workout_id: int, exercise_id: int):
    return ok(
        client.post(
            f"/api/workouts/{workout_id}/exercises",
            headers=headers,
            json={"exercise_id": exercise_id},
        ),
        201,
    )


def add_set(client, headers, we_id: int, payload: dict):
    return ok(
        client.post(
            f"/api/workout-exercises/{we_id}/sets",
            headers=headers,
            json=payload,
        ),
        201,
    )


def get_workout(client, headers, workout_id: int):
    return ok(client.get(f"/api/workouts/{workout_id}", headers=headers))


def create_template(client, headers, name: str, exercises: list[dict]):
    return ok(
        client.post(
            "/api/templates",
            headers=headers,
            json={"name": name, "exercises": exercises},
        ),
        201,
    )
