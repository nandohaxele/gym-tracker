"""Internal command executor — no LLM, existing services only."""

import uuid

import pytest
from pydantic import ValidationError as PydanticValidationError

from app.commands import (
    AddExerciseCommand,
    CommandReason,
    CommandStatus,
    CreateSessionCommand,
    FinishSessionCommand,
    RecordSetCommand,
    StartTemplateCommand,
    execute_command,
)
from app.exercises.models import ExerciseSynonym
from app.exercises.normalization import normalize_name
from tests.helpers import (
    add_we,
    bench_id,
    create_personal_exercise,
    create_template,
    empty_workout,
    get_workout,
    ok,
    plank_id,
)


def test_create_session_is_active_owned(client, user_a, db):
    result = execute_command(
        db, user_a["user_id"], CreateSessionCommand(name="AI session")
    )
    assert result.status == CommandStatus.executed
    assert result.data["ended_at"] is None
    assert result.data["user_id"] == user_a["user_id"]
    assert result.data["exercises"] == []
    loaded = get_workout(client, user_a["headers"], result.data["id"])
    assert loaded["ended_at"] is None


def test_add_exercise_resolves_and_attaches(client, user_a, db):
    workout = empty_workout(client, user_a["headers"])
    result = execute_command(
        db,
        user_a["user_id"],
        AddExerciseCommand(query="Bench Press", workout_id=workout["id"]),
    )
    assert result.status == CommandStatus.executed
    assert result.data["exercise"]["name"] == "Bench Press"
    detail = get_workout(client, user_a["headers"], workout["id"])
    assert len(detail["exercises"]) == 1
    assert detail["exercises"][0]["id"] == result.data["id"]


def test_add_exercise_ambiguous_does_not_write(client, user_a, db):
    workout = empty_workout(client, user_a["headers"])
    first = create_personal_exercise(client, user_a["headers"], f"A {uuid.uuid4().hex[:6]}")
    second = create_personal_exercise(client, user_a["headers"], f"B {uuid.uuid4().hex[:6]}")
    for exercise_id in (first["id"], second["id"]):
        db.add(
            ExerciseSynonym(
                exercise_id=exercise_id,
                synonym="Clashpress",
                synonym_normalized="clashpress",
                locale="en",
            )
        )
    db.commit()

    result = execute_command(
        db,
        user_a["user_id"],
        AddExerciseCommand(query="Clashpress", workout_id=workout["id"]),
    )
    assert result.status == CommandStatus.needs_clarification
    assert result.reason == CommandReason.exercise
    assert {item["id"] for item in result.candidates} == {first["id"], second["id"]}
    detail = get_workout(client, user_a["headers"], workout["id"])
    assert detail["exercises"] == []


def test_add_exercise_archived_does_not_write(client, user_a, db):
    name = f"Gone {uuid.uuid4().hex[:6]}"
    archived = create_personal_exercise(client, user_a["headers"], name)
    ok(client.post(f"/api/exercises/{archived['id']}/archive", headers=user_a["headers"]))
    workout = empty_workout(client, user_a["headers"])
    result = execute_command(
        db,
        user_a["user_id"],
        AddExerciseCommand(query=name, workout_id=workout["id"]),
    )
    assert result.status == CommandStatus.error
    assert result.reason == CommandReason.not_found
    assert get_workout(client, user_a["headers"], workout["id"])["exercises"] == []


def test_finish_session_explicit_and_inferred(client, user_a, db):
    explicit = empty_workout(client, user_a["headers"], "Explicit")
    finished = execute_command(
        db,
        user_a["user_id"],
        FinishSessionCommand(workout_id=explicit["id"]),
    )
    assert finished.status == CommandStatus.executed
    assert finished.data["ended_at"] is not None

    again = execute_command(
        db,
        user_a["user_id"],
        FinishSessionCommand(workout_id=explicit["id"]),
    )
    assert again.status == CommandStatus.executed
    assert again.data["ended_at"] == finished.data["ended_at"]

    only = empty_workout(client, user_a["headers"], "Only active")
    inferred = execute_command(db, user_a["user_id"], FinishSessionCommand())
    assert inferred.status == CommandStatus.executed
    assert inferred.data["id"] == only["id"]
    assert inferred.data["ended_at"] is not None


def test_finish_session_zero_and_many_active(client, user_a, db):
    none = execute_command(db, user_a["user_id"], FinishSessionCommand())
    assert none.status == CommandStatus.error
    assert none.reason == CommandReason.session

    first = empty_workout(client, user_a["headers"], "A")
    second = empty_workout(client, user_a["headers"], "B")
    many = execute_command(db, user_a["user_id"], FinishSessionCommand())
    assert many.status == CommandStatus.needs_clarification
    assert many.reason == CommandReason.session
    assert {item["id"] for item in many.candidates} == {first["id"], second["id"]}
    assert get_workout(client, user_a["headers"], first["id"])["ended_at"] is None
    assert get_workout(client, user_a["headers"], second["id"])["ended_at"] is None


def test_start_template_id_and_query(client, user_a, db):
    bench = bench_id(client, user_a["headers"])
    template = create_template(
        client,
        user_a["headers"],
        f"Start me {uuid.uuid4().hex[:6]}",
        [{"exercise_id": bench, "target_sets": 3, "target_reps_min": 8, "target_reps_max": 10}],
    )
    by_id = execute_command(
        db,
        user_a["user_id"],
        StartTemplateCommand(template_id=template["id"]),
    )
    assert by_id.status == CommandStatus.executed
    assert by_id.data["source_template_id"] == template["id"]
    assert by_id.data["ended_at"] is None
    assert by_id.data["exercises"][0]["planned_sets"] == 3
    assert by_id.data["exercises"][0]["sets"] == []

    by_query = execute_command(
        db,
        user_a["user_id"],
        StartTemplateCommand(query=template["name"]),
    )
    assert by_query.status == CommandStatus.executed
    assert by_query.data["id"] != by_id.data["id"]
    assert by_query.data["exercises"][0]["sets"] == []


def test_start_template_no_match_does_not_write(client, user_a, db):
    before = ok(client.get("/api/workouts", headers=user_a["headers"]))
    result = execute_command(
        db, user_a["user_id"], StartTemplateCommand(query="no such template")
    )
    assert result.status == CommandStatus.error
    assert result.reason == CommandReason.not_found
    after = ok(client.get("/api/workouts", headers=user_a["headers"]))
    assert len(after) == len(before)


def test_record_set_explicit_we_and_tracking_rule(client, user_a, db):
    workout = empty_workout(client, user_a["headers"])
    we = add_we(client, user_a["headers"], workout["id"], bench_id(client, user_a["headers"]))
    recorded = execute_command(
        db,
        user_a["user_id"],
        RecordSetCommand(workout_exercise_id=we["id"], reps=8, weight_kg=60),
    )
    assert recorded.status == CommandStatus.executed
    assert recorded.data["reps"] == 8
    assert recorded.data["weight_kg"] == 60

    plank = add_we(client, user_a["headers"], workout["id"], plank_id(client, user_a["headers"]))
    rejected = execute_command(
        db,
        user_a["user_id"],
        RecordSetCommand(workout_exercise_id=plank["id"], reps=10),
    )
    assert rejected.status == CommandStatus.error
    assert rejected.reason == CommandReason.validation
    detail = get_workout(client, user_a["headers"], workout["id"])
    plank_sets = next(row["sets"] for row in detail["exercises"] if row["id"] == plank["id"])
    assert plank_sets == []


def test_record_set_malformed_and_multiple_targets(client, user_a, db):
    with pytest.raises(PydanticValidationError):
        RecordSetCommand(workout_exercise_id=1, reps=-1)
    with pytest.raises(PydanticValidationError):
        RecordSetCommand(workout_exercise_id=1, distance_meters=0)
    with pytest.raises(PydanticValidationError):
        RecordSetCommand(workout_exercise_id=1, set_type="giant")
    with pytest.raises(PydanticValidationError):
        AddExerciseCommand(query="   ")
    with pytest.raises(PydanticValidationError):
        StartTemplateCommand(query="Push", scope="both")

    workout = empty_workout(client, user_a["headers"])
    add_we(client, user_a["headers"], workout["id"], bench_id(client, user_a["headers"]))
    add_we(client, user_a["headers"], workout["id"], plank_id(client, user_a["headers"]))
    unclear = execute_command(
        db,
        user_a["user_id"],
        RecordSetCommand(workout_id=workout["id"], reps=5),
    )
    assert unclear.status == CommandStatus.needs_clarification
    assert unclear.reason == CommandReason.workout_exercise
    assert len(unclear.candidates) == 2
    assert {item["id"] for item in unclear.candidates}

    named = execute_command(
        db,
        user_a["user_id"],
        RecordSetCommand(workout_id=workout["id"], exercise_query="Bench Press", reps=5),
    )
    assert named.status == CommandStatus.executed
    assert named.data["reps"] == 5


def test_record_set_does_not_pick_among_active_sessions(client, user_a, db):
    first = empty_workout(client, user_a["headers"], "S1")
    second = empty_workout(client, user_a["headers"], "S2")
    add_we(client, user_a["headers"], first["id"], bench_id(client, user_a["headers"]))
    result = execute_command(
        db, user_a["user_id"], RecordSetCommand(reps=5)
    )
    assert result.status == CommandStatus.needs_clarification
    assert result.reason == CommandReason.session
    assert {item["id"] for item in result.candidates} == {first["id"], second["id"]}
    assert get_workout(client, user_a["headers"], first["id"])["exercises"][0]["sets"] == []
