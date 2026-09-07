"""Runtime SQLite FK enforcement. Skipped until PRAGMA is enabled on the app engine."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from tests.helpers import add_set, add_we, bench_id, create_template, empty_workout, get_workout, ok


@pytest.fixture
def require_fk(db):
    enabled = db.execute(text("PRAGMA foreign_keys")).scalar()
    if not enabled:
        pytest.skip("PRAGMA foreign_keys is still off on the application engine")


def test_pragma_is_on_when_enabled(db, require_fk):
    assert db.execute(text("PRAGMA foreign_keys")).scalar() == 1


def test_exercise_restrict_blocks_catalog_delete(client, user_a, db, require_fk):
    workout = empty_workout(client, user_a["headers"])
    bench = bench_id(client, user_a["headers"])
    add_we(client, user_a["headers"], workout["id"], bench)
    with pytest.raises(IntegrityError):
        db.execute(text("DELETE FROM exercises WHERE id = :id"), {"id": bench})
        db.commit()
    db.rollback()
    assert db.execute(text("SELECT count(*) FROM exercises WHERE id = :id"), {"id": bench}).scalar() == 1


def test_workout_cascade_and_template_set_null(client, user_a, db, require_fk):
    bench = bench_id(client, user_a["headers"])
    template = create_template(
        client,
        user_a["headers"],
        "FK source",
        [{"exercise_id": bench, "target_sets": 1, "target_reps_min": 5, "target_reps_max": 5}],
    )
    started = ok(
        client.post(f"/api/templates/{template['id']}/start", headers=user_a["headers"]),
        201,
    )
    we_id = started["exercises"][0]["id"]
    recorded = add_set(client, user_a["headers"], we_id, {"reps": 5, "weight_kg": 20})

    db.execute(text("DELETE FROM templates WHERE id = :id"), {"id": template["id"]})
    db.commit()
    leftover = db.execute(
        text("SELECT count(*) FROM template_exercises WHERE template_id = :id"),
        {"id": template["id"]},
    ).scalar()
    assert leftover == 0
    provenance = db.execute(
        text("SELECT source_template_id FROM workouts WHERE id = :id"),
        {"id": started["id"]},
    ).scalar()
    assert provenance is None
    snapshot = get_workout(client, user_a["headers"], started["id"])
    assert snapshot["exercises"][0]["planned_sets"] == 1

    ok(client.delete(f"/api/workouts/{started['id']}", headers=user_a["headers"]))
    assert (
        db.execute(
            text("SELECT count(*) FROM workout_exercises WHERE id = :id"),
            {"id": we_id},
        ).scalar()
        == 0
    )
    assert (
        db.execute(text("SELECT count(*) FROM sets WHERE id = :id"), {"id": recorded["id"]}).scalar()
        == 0
    )
