"""Trusted context, interpretation validation, and Phase 8 orchestration.

No ORM writes. All mutations go through execute_command.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Optional

from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.orm import Session

from app.assistant.models import (
    CommandPreview,
    ExecuteCommandIn,
    ExecuteOut,
    ExecuteResultItem,
    InterpretOut,
    ProviderIntent,
    ProviderInterpretation,
    confirmation_required_for,
)
from app.assistant.provider import (
    AssistantProvider,
    AssistantProviderError,
    AssistantUnavailable,
    get_provider,
)
from app.commands.execute import execute_command
from app.commands.models import (
    AddExerciseCommand,
    Command,
    CommandResult,
    CommandStatus,
    CreateSessionCommand,
    FinishSessionCommand,
    RecordSetCommand,
    StartTemplateCommand,
)
from app.core.config import get_settings
from app.core.exceptions import NotFoundError, ValidationError
from app.exercises.normalization import normalize_name
from app.exercises.service import list_exercises, resolve_exercise
from app.templates.service import list_templates, resolve_template
from app.workouts.models import Set, Workout, WorkoutExercise
from app.workouts.schemas import WorkoutSummary
from app.workouts.service import (
    get_workout,
    get_workout_exercise,
    list_active_workouts,
)


@dataclass
class TrustedContext:
    workout: Optional[Workout] = None
    focus: Optional[WorkoutExercise] = None
    actives: list[Workout] = field(default_factory=list)
    locale: Optional[str] = None


def interpret_utterance(
    db: Session,
    user_id: int,
    text: str,
    *,
    workout_id: Optional[int] = None,
    focus_workout_exercise_id: Optional[int] = None,
    locale: Optional[str] = None,
    provider: Optional[AssistantProvider] = None,
) -> InterpretOut:
    """Read-only interpretation. Never writes."""
    transcript = text.strip()
    try:
        trusted = build_trusted_context(
            db,
            user_id,
            workout_id=workout_id,
            focus_workout_exercise_id=focus_workout_exercise_id,
            locale=locale,
        )
    except (NotFoundError, ValidationError) as exc:
        return InterpretOut(
            status="error",
            transcript=transcript,
            message=str(exc),
            reason="validation",
        )

    model_context = context_for_model(db, user_id, trusted)
    try:
        parsed = (provider or get_provider()).interpret(transcript, model_context)
    except AssistantUnavailable:
        return InterpretOut(
            status="unavailable",
            transcript=transcript,
            message="Voice assistant is not configured",
        )
    except AssistantProviderError as exc:
        return InterpretOut(
            status="error",
            transcript=transcript,
            message=exc.message,
            reason=exc.category,
        )

    try:
        return _from_provider(db, user_id, transcript, parsed, trusted)
    except PydanticValidationError:
        return InterpretOut(
            status="error",
            transcript=transcript,
            message="Assistant returned an invalid interpretation",
            reason="malformed",
        )


def execute_assistant(
    db: Session,
    user_id: int,
    items: list[ExecuteCommandIn],
) -> ExecuteOut:
    """Validate and run Phase 8 commands. No LLM."""
    settings = get_settings()
    if len(items) > settings.assistant_max_commands:
        raise ValidationError(
            f"At most {settings.assistant_max_commands} commands are allowed"
        )

    commands = [_to_phase8(item) for item in items]
    results: list[ExecuteResultItem] = []
    pending_we_id: Optional[int] = None
    pending_names: set[str] = set()

    for command in commands:
        command = _bind_new_exercise(command, pending_we_id, pending_names)
        result = execute_command(db, user_id, command)
        item = _result_item(command, result)
        results.append(item)
        if result.status != CommandStatus.executed:
            return ExecuteOut(
                status=result.status.value,
                results=results,
                executed=[row for row in results if row.status == "executed"],
                failed=item,
                reason=result.reason.value if result.reason else None,
                message=result.message,
                candidates=result.candidates,
            )
        if isinstance(command, AddExerciseCommand) and isinstance(result.data, dict):
            pending_we_id = result.data.get("id")
            pending_names = {normalize_name(command.query)}
            exercise = result.data.get("exercise") or {}
            name = exercise.get("name")
            if name:
                pending_names.add(normalize_name(name))

    return ExecuteOut(
        status="executed",
        results=results,
        executed=results,
    )


def build_trusted_context(
    db: Session,
    user_id: int,
    *,
    workout_id: Optional[int],
    focus_workout_exercise_id: Optional[int],
    locale: Optional[str],
) -> TrustedContext:
    focus: Optional[WorkoutExercise] = None
    workout: Optional[Workout] = None

    if focus_workout_exercise_id is not None:
        focus = get_workout_exercise(db, user_id, focus_workout_exercise_id)
        if workout_id is not None and focus.workout_id != workout_id:
            raise ValidationError(
                "focus_workout_exercise_id does not belong to workout_id"
            )
        workout = get_workout(db, user_id, focus.workout_id)

    if workout_id is not None and workout is None:
        workout = get_workout(db, user_id, workout_id)

    actives = list_active_workouts(db, user_id)
    return TrustedContext(
        workout=workout, focus=focus, actives=actives, locale=locale
    )


def context_for_model(
    db: Session, user_id: int, trusted: TrustedContext
) -> dict[str, Any]:
    """Minimal names-and-metrics snapshot. No catalog ids."""
    session_block: Optional[dict[str, Any]] = None
    if trusted.workout is not None:
        session_block = {
            "name": trusted.workout.name,
            "date": str(trusted.workout.date),
            "active": trusted.workout.ended_at is None,
            "exercises": [
                _we_snapshot(row) for row in trusted.workout.exercises
            ],
        }

    focus_name = None
    if trusted.focus is not None and trusted.focus.exercise is not None:
        focus_name = trusted.focus.exercise.name

    catalog = []
    for exercise in list_exercises(db, user_id):
        catalog.append(
            {
                "name": exercise.name,
                "synonyms": [row.synonym for row in exercise.synonyms],
                "primary": exercise.primary_tracking_type,
            }
        )

    templates = [
        {
            "name": row.name,
            "scope": "global" if row.user_id is None else "personal",
        }
        for row in list_templates(db, user_id)
    ]

    return {
        "locale": trusted.locale,
        "has_explicit_session": trusted.workout is not None,
        "focus_exercise": focus_name,
        "session": session_block,
        "active_session_count": len(trusted.actives),
        "active_session_names": [row.name for row in trusted.actives],
        "catalog": catalog,
        "templates": templates,
    }


def _we_snapshot(row: WorkoutExercise) -> dict[str, Any]:
    exercise = row.exercise
    last = _last_persisted_set(row)
    return {
        "name": None if exercise is None else exercise.name,
        "primary": None if exercise is None else exercise.primary_tracking_type,
        "planned_sets": row.planned_sets,
        "last_set": None
        if last is None
        else {
            "reps": last.reps,
            "weight_kg": None if last.weight_kg is None else str(last.weight_kg),
            "duration_seconds": last.duration_seconds,
            "distance_meters": last.distance_meters,
        },
    }


def _last_persisted_set(row: WorkoutExercise) -> Optional[Set]:
    sets = list(row.sets or [])
    if not sets:
        return None
    return max(sets, key=lambda item: (item.order_index, item.id))


def _from_provider(
    db: Session,
    user_id: int,
    transcript: str,
    parsed: ProviderInterpretation,
    trusted: TrustedContext,
) -> InterpretOut:
    settings = get_settings()
    if parsed.status == "unknown":
        return InterpretOut(
            status="unknown",
            transcript=transcript,
            message=parsed.message or "I could not understand that command",
        )

    if len(parsed.intents) > settings.assistant_max_commands:
        return InterpretOut(
            status="error",
            transcript=transcript,
            message=f"At most {settings.assistant_max_commands} commands are allowed",
            reason="validation",
        )

    if parsed.status == "needs_clarification" and not parsed.intents:
        return InterpretOut(
            status="needs_clarification",
            transcript=transcript,
            message=parsed.message or "Please choose an option",
            reason="unknown",
        )

    commands: list[Command] = []
    for intent in parsed.intents:
        built = _intent_to_command(intent, trusted)
        if isinstance(built, RecordSetCommand):
            built, blocked = _fill_record_set(intent, built, trusted)
            if blocked is not None:
                return blocked.model_copy(update={"transcript": transcript})
        commands.append(built)

    session_block = _session_preflight(commands, trusted)
    if session_block is not None:
        return session_block.model_copy(update={"transcript": transcript})

    resolve_block = _resolver_preflight(db, user_id, commands, trusted)
    if resolve_block is not None:
        return resolve_block.model_copy(update={"transcript": transcript})

    previews = [_preview_command(command, trusted) for command in commands]
    confirmation = any(item.confirmation_required for item in previews)
    return InterpretOut(
        status="ready",
        transcript=transcript,
        confirmation_required=confirmation,
        commands=previews,
        preview=" → ".join(item.preview for item in previews),
    )


def _intent_to_command(intent: ProviderIntent, trusted: TrustedContext) -> Command:
    workout_id = None if trusted.workout is None else trusted.workout.id
    locale = intent.locale or trusted.locale

    if intent.type == "create_session":
        name = (intent.name or "").strip() or "Workout"
        return CreateSessionCommand(name=name, date=intent.date)
    if intent.type == "add_exercise":
        query = (intent.query or "").strip()
        if not query:
            raise PydanticValidationError.from_exception_data(
                "AddExerciseCommand",
                [
                    {
                        "type": "missing",
                        "loc": ("query",),
                        "msg": "Field required",
                        "input": None,
                    }
                ],
            )
        return AddExerciseCommand(
            query=query, locale=locale, workout_id=workout_id
        )
    if intent.type == "record_set":
        focus_id = None if trusted.focus is None else trusted.focus.id
        return RecordSetCommand(
            workout_id=workout_id,
            workout_exercise_id=focus_id,
            exercise_query=(intent.exercise_query or intent.query) or None,
            locale=locale,
            reps=intent.reps,
            weight_kg=intent.weight_kg,
            duration_seconds=intent.duration_seconds,
            distance_meters=intent.distance_meters,
        )
    if intent.type == "finish_session":
        return FinishSessionCommand(workout_id=workout_id)
    if intent.type == "start_template":
        query = (intent.query or "").strip()
        if not query:
            raise PydanticValidationError.from_exception_data(
                "StartTemplateCommand",
                [
                    {
                        "type": "missing",
                        "loc": ("query",),
                        "msg": "Field required",
                        "input": None,
                    }
                ],
            )
        return StartTemplateCommand(query=query, scope=intent.scope)
    raise ValidationError(f"Unsupported command type: {intent.type}")


def _fill_record_set(
    intent: ProviderIntent,
    command: RecordSetCommand,
    trusted: TrustedContext,
) -> tuple[RecordSetCommand, Optional[InterpretOut]]:
    needs_last = (
        intent.use_last_reps
        or intent.use_last_weight
        or intent.use_last_duration
        or intent.use_last_distance
        or intent.weight_delta_kg is not None
    )
    if not needs_last:
        return command, None

    target = _incremental_target(trusted, command)
    if target is None:
        return command, InterpretOut(
            status="needs_clarification",
            transcript="",
            reason="workout_exercise",
            message="Which exercise should I update?",
            candidates=_we_candidates(trusted),
        )

    last = _last_persisted_set(target)
    if last is None:
        return command, InterpretOut(
            status="needs_clarification",
            transcript="",
            reason="validation",
            message="No recorded set to copy from",
        )

    updates: dict[str, Any] = {"workout_exercise_id": target.id}
    if trusted.workout is not None:
        updates["workout_id"] = trusted.workout.id

    if intent.use_last_reps:
        if last.reps is None:
            return command, _missing_last("reps")
        updates["reps"] = last.reps
    if intent.use_last_duration:
        if last.duration_seconds is None:
            return command, _missing_last("duration")
        updates["duration_seconds"] = last.duration_seconds
    if intent.use_last_distance:
        if last.distance_meters is None:
            return command, _missing_last("distance")
        updates["distance_meters"] = last.distance_meters

    if intent.use_last_weight or intent.weight_delta_kg is not None:
        if last.weight_kg is None:
            return command, _missing_last("weight")
        weight = Decimal(last.weight_kg)
        if intent.weight_delta_kg is not None:
            weight = weight + Decimal(intent.weight_delta_kg)
        if weight < 0:
            return command, InterpretOut(
                status="error",
                transcript="",
                reason="validation",
                message="Weight cannot be negative",
            )
        updates["weight_kg"] = weight

    return command.model_copy(update=updates), None


def _missing_last(label: str) -> InterpretOut:
    return InterpretOut(
        status="needs_clarification",
        transcript="",
        reason="validation",
        message=f"No recorded {label} to copy",
    )


def _incremental_target(
    trusted: TrustedContext, command: RecordSetCommand
) -> Optional[WorkoutExercise]:
    if trusted.focus is not None:
        return trusted.focus
    if trusted.workout is None:
        return None
    rows = list(trusted.workout.exercises)
    query = command.exercise_query
    if query:
        normalized = normalize_name(query)
        rows = [
            row
            for row in rows
            if row.exercise is not None
            and normalize_name(row.exercise.name) == normalized
        ]
    if len(rows) == 1:
        return rows[0]
    return None


def _we_candidates(trusted: TrustedContext) -> list[dict[str, Any]]:
    if trusted.workout is None:
        return []
    candidates = []
    for row in trusted.workout.exercises:
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


def _session_preflight(
    commands: list[Command], trusted: TrustedContext
) -> Optional[InterpretOut]:
    needs_session = any(
        isinstance(command, (AddExerciseCommand, RecordSetCommand, FinishSessionCommand))
        for command in commands
    )
    if not needs_session:
        return None
    if trusted.workout is not None:
        return None
    if len(trusted.actives) == 0:
        return InterpretOut(
            status="needs_clarification",
            transcript="",
            reason="session",
            message="No active session",
            candidates=[],
        )
    if len(trusted.actives) > 1:
        return InterpretOut(
            status="needs_clarification",
            transcript="",
            reason="session",
            message="Multiple active sessions",
            candidates=[
                WorkoutSummary.model_validate(row).model_dump(mode="json")
                for row in trusted.actives
            ],
        )

    workout_id = trusted.actives[0].id
    if trusted.workout is None:
        trusted.workout = trusted.actives[0]
    for index, command in enumerate(commands):
        if isinstance(
            command, (AddExerciseCommand, RecordSetCommand, FinishSessionCommand)
        ) and getattr(command, "workout_id", None) is None:
            commands[index] = command.model_copy(update={"workout_id": workout_id})
    return None


def _resolver_preflight(
    db: Session,
    user_id: int,
    commands: list[Command],
    trusted: TrustedContext,
) -> Optional[InterpretOut]:
    for command in commands:
        if isinstance(command, AddExerciseCommand):
            resolution = resolve_exercise(
                db, user_id, command.query, locale=command.locale
            )
            if resolution.ambiguous:
                return InterpretOut(
                    status="needs_clarification",
                    transcript="",
                    reason="exercise",
                    message="Multiple exercises match this query",
                    candidates=[
                        {
                            "id": row.id,
                            "name": row.name,
                            "primary_tracking_type": row.primary_tracking_type,
                        }
                        for row in resolution.candidates
                    ],
                    commands=[_preview_command(command, trusted)],
                )
            if not resolution.resolved:
                return InterpretOut(
                    status="unknown",
                    transcript="",
                    reason="not_found",
                    message="Exercise not found",
                )
        elif isinstance(command, StartTemplateCommand) and command.template_id is None:
            resolution = resolve_template(
                db, user_id, command.query, scope=command.scope
            )
            if resolution.ambiguous:
                return InterpretOut(
                    status="needs_clarification",
                    transcript="",
                    reason="template",
                    message="Multiple templates match this query",
                    candidates=[
                        {
                            "id": row.id,
                            "name": row.name,
                            "is_global": row.user_id is None,
                        }
                        for row in resolution.candidates
                    ],
                    commands=[_preview_command(command, trusted)],
                )
            if not resolution.resolved:
                return InterpretOut(
                    status="unknown",
                    transcript="",
                    reason="not_found",
                    message="Template not found",
                )
            index = commands.index(command)
            commands[index] = command.model_copy(
                update={"template_id": resolution.template.id}
            )
        elif isinstance(command, RecordSetCommand):
            blocked = _record_set_preflight(command, trusted)
            if blocked is not None:
                return blocked
    return None


def _record_set_preflight(
    command: RecordSetCommand, trusted: TrustedContext
) -> Optional[InterpretOut]:
    if command.workout_exercise_id is not None:
        return None
    if trusted.workout is None:
        return None
    rows = list(trusted.workout.exercises)
    if command.exercise_query:
        normalized = normalize_name(command.exercise_query)
        rows = [
            row
            for row in rows
            if row.exercise is not None
            and normalize_name(row.exercise.name) == normalized
        ]
        # Newly added exercise in a compound command may not be on the Session yet.
        if len(rows) == 0 and any(
            True
            for _ in [command]
        ):
            return None
    if len(rows) > 1:
        return InterpretOut(
            status="needs_clarification",
            transcript="",
            reason="workout_exercise",
            message="Multiple workout exercises match",
            candidates=_we_candidates(trusted),
            commands=[_preview_command(command, trusted)],
        )
    if len(rows) == 1:
        command.workout_exercise_id = rows[0].id
    return None


def _preview_command(command: Command, trusted: TrustedContext) -> CommandPreview:
    payload = command.model_dump(mode="json", exclude_none=True)
    if isinstance(command, CreateSessionCommand):
        kind = "create_session"
        preview = f"Create workout: {command.name}"
    elif isinstance(command, AddExerciseCommand):
        kind = "add_exercise"
        preview = f"Add exercise: {command.query}"
    elif isinstance(command, RecordSetCommand):
        kind = "record_set"
        bits = []
        if command.reps is not None:
            bits.append(f"{command.reps} reps")
        if command.weight_kg is not None:
            bits.append(f"{command.weight_kg} kg")
        if command.duration_seconds is not None:
            bits.append(f"{command.duration_seconds}s")
        if command.distance_meters is not None:
            bits.append(f"{command.distance_meters} m")
        preview = "Log set" if not bits else "Log set: " + ", ".join(bits)
    elif isinstance(command, FinishSessionCommand):
        kind = "finish_session"
        name = trusted.workout.name if trusted.workout is not None else "workout"
        if command.workout_id and trusted.workout is None:
            match = next(
                (row for row in trusted.actives if row.id == command.workout_id),
                None,
            )
            if match is not None:
                name = match.name
        preview = f"Finish workout: {name}"
    else:
        kind = "start_template"
        label = command.query or f"template {command.template_id}"
        preview = f"Start template: {label}"
    payload["type"] = kind
    return CommandPreview(
        type=kind,
        payload=payload,
        confirmation_required=confirmation_required_for(kind),
        preview=preview,
    )


def _to_phase8(item: ExecuteCommandIn) -> Command:
    if item.type == "create_session":
        return CreateSessionCommand(
            name=item.name or "Workout", date=item.date
        )
    if item.type == "add_exercise":
        return AddExerciseCommand(
            query=item.query or "",
            locale=item.locale,
            workout_id=item.workout_id,
        )
    if item.type == "record_set":
        return RecordSetCommand(
            workout_exercise_id=item.workout_exercise_id,
            workout_id=item.workout_id,
            exercise_query=item.exercise_query,
            locale=item.locale,
            reps=item.reps,
            weight_kg=item.weight_kg,
            duration_seconds=item.duration_seconds,
            distance_meters=item.distance_meters,
            rpe=item.rpe,
            rir=item.rir,
            set_type=item.set_type,
        )
    if item.type == "finish_session":
        return FinishSessionCommand(workout_id=item.workout_id)
    return StartTemplateCommand(
        template_id=item.template_id,
        query=item.query,
        scope=item.scope,
    )


def _bind_new_exercise(
    command: Command,
    pending_we_id: Optional[int],
    pending_names: set[str],
) -> Command:
    if not isinstance(command, RecordSetCommand):
        return command
    if command.workout_exercise_id is not None or pending_we_id is None:
        return command
    query = command.exercise_query
    if query and normalize_name(query) not in pending_names:
        return command
    return command.model_copy(update={"workout_exercise_id": pending_we_id})


def _result_item(command: Command, result: CommandResult) -> ExecuteResultItem:
    if isinstance(command, CreateSessionCommand):
        kind = "create_session"
    elif isinstance(command, AddExerciseCommand):
        kind = "add_exercise"
    elif isinstance(command, RecordSetCommand):
        kind = "record_set"
    elif isinstance(command, FinishSessionCommand):
        kind = "finish_session"
    else:
        kind = "start_template"
    return ExecuteResultItem(
        type=kind,
        status=result.status.value,
        reason=result.reason.value if result.reason else None,
        message=result.message,
        data=result.data,
        candidates=result.candidates,
    )
