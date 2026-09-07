"""Stable WorkoutExercise / Set IDs, compact order, granular CRUD."""

from tests.helpers import add_set, add_we, bench_id, empty_workout, get_workout, ok, squat_id


def _ids(items):
    return [item["id"] for item in items]


def test_set_crud_keeps_sibling_ids_and_compacts(client, user_a):
    headers = user_a["headers"]
    workout = empty_workout(client, headers)
    we = add_we(client, headers, workout["id"], bench_id(client, headers))
    first = add_set(client, headers, we["id"], {"reps": 8, "weight_kg": 50})
    second = add_set(client, headers, we["id"], {"reps": 8, "weight_kg": 52.5})
    third = add_set(client, headers, we["id"], {"reps": 6, "weight_kg": 55})
    before = {first["id"], second["id"], third["id"]}

    patched = ok(
        client.patch(
            f"/api/sets/{second['id']}",
            headers=headers,
            json={"reps": 7, "weight_kg": 53},
        )
    )
    assert patched["id"] == second["id"]

    ok(client.delete(f"/api/sets/{first['id']}", headers=headers))
    detail = get_workout(client, headers, workout["id"])
    sets = detail["exercises"][0]["sets"]
    assert _ids(sets) == [second["id"], third["id"]]
    assert [row["order_index"] for row in sets] == [0, 1]
    assert before.issuperset(_ids(sets))

    reordered = ok(
        client.post(
            f"/api/workout-exercises/{we['id']}/sets/reorder",
            headers=headers,
            json={"ids": [third["id"], second["id"]]},
        )
    )
    assert _ids(reordered["sets"]) == [third["id"], second["id"]]
    assert [row["order_index"] for row in reordered["sets"]] == [0, 1]


def test_workout_exercise_crud_keeps_sibling_ids(client, user_a):
    headers = user_a["headers"]
    workout = empty_workout(client, headers)
    we_a = add_we(client, headers, workout["id"], bench_id(client, headers))
    we_b = add_we(client, headers, workout["id"], squat_id(client, headers))
    set_a = add_set(client, headers, we_a["id"], {"reps": 5, "weight_kg": 80})
    set_b = add_set(client, headers, we_b["id"], {"reps": 5, "weight_kg": 100})

    ok(client.delete(f"/api/workout-exercises/{we_a['id']}", headers=headers))
    detail = get_workout(client, headers, workout["id"])
    assert _ids(detail["exercises"]) == [we_b["id"]]
    assert detail["exercises"][0]["order_index"] == 0
    assert _ids(detail["exercises"][0]["sets"]) == [set_b["id"]]
    remaining_sets = {s["id"] for we in detail["exercises"] for s in we["sets"]}
    assert set_a["id"] not in remaining_sets

    we_c = add_we(client, headers, workout["id"], bench_id(client, headers))
    reordered = ok(
        client.post(
            f"/api/workouts/{workout['id']}/exercises/reorder",
            headers=headers,
            json={"ids": [we_c["id"], we_b["id"]]},
        )
    )
    assert _ids(reordered["exercises"]) == [we_c["id"], we_b["id"]]
    assert [row["order_index"] for row in reordered["exercises"]] == [0, 1]
    assert reordered["exercises"][1]["sets"][0]["id"] == set_b["id"]
