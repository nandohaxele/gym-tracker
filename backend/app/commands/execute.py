"""Execute structured commands by calling existing domain services.

No raw INSERT/UPDATE/DELETE. `user_id` comes only from the trusted caller.
"""

from typing import Optional

from sqlalchemy.orm import Session

from app.commands.models import (
    AddExerciseCommand,
    Command,
    CommandReason,
    CommandResult,
    CommandStatus,
    CreateSessionCommand,
    FinishSessionCommand,
    RecordSetCommand,
    StartTemplateCommand,
)
from app.core.exceptions import AppError, ConflictError, NotFoundError, ValidationError
from app.exercises.schemas import ExerciseOut
from app.exercises.service import resolve_exercise
from app.templates.schemas import TemplateSummary
from app.templates.service import resolve_template, start_template
from app.workouts.models import Workout, WorkoutExercise
from app.workouts.schemas import (
    SetIn,
    SetOut,
    WorkoutCreate,
    WorkoutDetail,
    WorkoutExerciseCreate,
    WorkoutExerciseOut,
    WorkoutSummary,
)
from app.workouts.service import (
    add_set,
    add_workout_exercise,
    complete_workout,
    create_workout,
    get_workout,
    get_workout_exercise,
    list_active_workouts,
)


def execute_command(db: Session, user_id: int, command: Command) -> CommandResult:
    """Dispatch one command. Never reads `user_id` from the command payload."""
    try:
        if isinstance(command, CreateSessionCommand):
            return _create_session(db, user_id, command)
        if isinstance(command, AddExerciseCommand):
            return _add_exercise(db, user_id, command)
        if isinstance(command, RecordSetCommand):
            return _record_set(db, user_id, command)
        if isinstance(command, FinishSessionCommand):
            return _finish_session(db, user_id, command)
        if isinstance(command, StartTemplateCommand):
            return _start_template(db, user_id, command)
        raise ValidationError(f"Unsupported command type: {type(command).__name__}")
    except AppError as exc:
        return _from_domain_error(exc)


def _from_domain_error(exc: AppError) -> CommandResult:
    if isinstance(exc, NotFoundError):
        reason = CommandReason.not_found
    elif isinstance(exc, ConflictError):
        reason = CommandReason.conflict
    else:
        reason = CommandReason.validation
    return CommandResult(
        status=CommandStatus.error, reason=reason, message=str(exc)
    )


def _workout_data(workout: Workout) -> dict:
    return WorkoutDetail.model_validate(workout).model_dump(mode="json")


def _session_candidates(rows: list[Workout]) -> list[dict]:
    return [WorkoutSummary.model_validate(row).model_dump(mode="json") for row in rows]


def _exercise_candidates(rows) -> list[dict]:
    return [ExerciseOut.model_validate(row).model_dump(mode="json") for row in rows]


def _template_candidates(rows) -> list[dict]:
    return [TemplateSummary.model_validate(row).model_dump(mode="json") for row in rows]


def _we_candidates(rows: list[WorkoutExercise]) -> list[dict]:
    candidates: list[dict] = []
    for row in rows:
        exercise = row.exercise
        candidates.append(
            {
                "id": row.id,
                "exercise_id": row.exercise_id,
                "exercise_name": None if exercise is None else exercise.name,
                "primary_tracking_type": (
                    None if exercise is None else exercise.primary_tracking_type
                ),
            }
        )
    return candidates


def _target_session(
    db: Session, user_id: int, workout_id: Optional[int]
) -> tuple[Optional[Workout], Optional[CommandResult]]:
    if workout_id is not None:
        return get_workout(db, user_id, workout_id), None

    actives = list_active_workouts(db, user_id)
    if len(actives) == 0:
        return None, CommandResult(
            status=CommandStatus.error,
            reason=CommandReason.session,
            message="No active session",
        )
    if len(actives) > 1:
        return None, CommandResult(
            status=CommandStatus.needs_clarification,
            reason=CommandReason.session,
            message="Multiple active sessions",
            candidates=_session_candidates(actives),
        )
    return actives[0], None


def _create_session(
    db: Session, user_id: int, command: CreateSessionCommand
) -> CommandResult:
    workout = create_workout(
        db,
        user_id,
        WorkoutCreate(name=command.name, date=command.date, exercises=[]),
    )
    return CommandResult(status=CommandStatus.executed, data=_workout_data(workout))


def _add_exercise(
    db: Session, user_id: int, command: AddExerciseCommand
) -> CommandResult:
    workout, blocked = _target_session(db, user_id, command.workout_id)
    if blocked is not None:
        return blocked
    assert workout is not None

    resolution = resolve_exercise(
        db, user_id, command.query, locale=command.locale
    )
    if resolution.ambiguous:
        return CommandResult(
            status=CommandStatus.needs_clarification,
            reason=CommandReason.exercise,
            message="Multiple exercises match this query",
            candidates=_exercise_candidates(resolution.candidates),
        )
    if not resolution.resolved:
        return CommandResult(
            status=CommandStatus.error,
            reason=CommandReason.not_found,
            message="Exercise not found",
        )

    row = add_workout_exercise(
        db,
        user_id,
        workout.id,
        WorkoutExerciseCreate(exercise_id=resolution.exercise.id),
    )
    return CommandResult(
        status=CommandStatus.executed,
        data=WorkoutExerciseOut.model_validate(row).model_dump(mode="json"),
    )


def _record_set(
    db: Session, user_id: int, command: RecordSetCommand
) -> CommandResult:
    payload = SetIn(
        reps=command.reps,
        weight_kg=command.weight_kg,
        duration_seconds=command.duration_seconds,
        distance_meters=command.distance_meters,
        rpe=command.rpe,
        rir=command.rir,
        set_type=command.set_type,
    )

    we_id = command.workout_exercise_id
    if we_id is not None:
        if command.workout_id is not None:
            we = get_workout_exercise(db, user_id, we_id)
            if we.workout_id != command.workout_id:
                return CommandResult(
                    status=CommandStatus.error,
                    reason=CommandReason.validation,
                    message="workout_exercise_id does not belong to workout_id",
                )
        row = add_set(db, user_id, we_id, payload)
        return CommandResult(
            status=CommandStatus.executed,
            data=SetOut.model_validate(row).model_dump(mode="json"),
        )

    workout, blocked = _target_session(db, user_id, command.workout_id)
    if blocked is not None:
        return blocked
    assert workout is not None
    detail = get_workout(db, user_id, workout.id)
    targets = list(detail.exercises)

    if command.exercise_query:
        resolution = resolve_exercise(
            db, user_id, command.exercise_query, locale=command.locale
        )
        if resolution.ambiguous:
            return CommandResult(
                status=CommandStatus.needs_clarification,
                reason=CommandReason.exercise,
                message="Multiple exercises match this query",
                candidates=_exercise_candidates(resolution.candidates),
            )
        if not resolution.resolved:
            return CommandResult(
                status=CommandStatus.error,
                reason=CommandReason.not_found,
                message="Exercise not found",
            )
        targets = [
            row for row in targets if row.exercise_id == resolution.exercise.id
        ]

    if len(targets) == 0:
        return CommandResult(
            status=CommandStatus.error,
            reason=CommandReason.workout_exercise,
            message="No matching workout exercise",
        )
    if len(targets) > 1:
        return CommandResult(
            status=CommandStatus.needs_clarification,
            reason=CommandReason.workout_exercise,
            message="Multiple workout exercises match",
            candidates=_we_candidates(targets),
        )

    row = add_set(db, user_id, targets[0].id, payload)
    return CommandResult(
        status=CommandStatus.executed,
        data=SetOut.model_validate(row).model_dump(mode="json"),
    )


def _finish_session(
    db: Session, user_id: int, command: FinishSessionCommand
) -> CommandResult:
    if command.workout_id is not None:
        workout = complete_workout(db, user_id, command.workout_id)
        return CommandResult(
            status=CommandStatus.executed, data=_workout_data(workout)
        )

    workout, blocked = _target_session(db, user_id, None)
    if blocked is not None:
        return blocked
    assert workout is not None
    completed = complete_workout(db, user_id, workout.id)
    return CommandResult(
        status=CommandStatus.executed, data=_workout_data(completed)
    )


def _start_template(
    db: Session, user_id: int, command: StartTemplateCommand
) -> CommandResult:
    template_id = command.template_id
    if template_id is None:
        resolution = resolve_template(
            db, user_id, command.query, scope=command.scope
        )
        if resolution.ambiguous:
            return CommandResult(
                status=CommandStatus.needs_clarification,
                reason=CommandReason.template,
                message="Multiple templates match this query",
                candidates=_template_candidates(resolution.candidates),
            )
        if not resolution.resolved:
            return CommandResult(
                status=CommandStatus.error,
                reason=CommandReason.not_found,
                message="Template not found",
            )
        template_id = resolution.template.id

    workout = start_template(db, user_id, template_id)
    return CommandResult(status=CommandStatus.executed, data=_workout_data(workout))
