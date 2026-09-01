"""Idempotent seeder for the predefined global exercise catalog.

Global exercises are matched by `slug`, so re-running never duplicates a row and
never renumbers an existing id. Personal exercises (`user_id IS NOT NULL`) are
invisible to this module: they are never read, updated, or promoted to global.

The seeder only ever *adds* what is missing -- an existing global's name, muscle
group or primary tracking is treated as data that a migration owns, not as seed
state to overwrite. That keeps repeated runs a no-op while still healing a
catalog row that somehow lost its tracking configuration.
"""

from dataclasses import dataclass

from sqlalchemy.orm import Session, selectinload

from app.exercises.models import (
    DEFAULT_SYNONYM_LOCALE,
    Exercise,
    ExerciseSynonym,
    ExerciseTracking,
)
from app.exercises.normalization import clean_display_name, normalize_name
from app.seed.exercises_seed import PREDEFINED_EXERCISES


@dataclass
class SeedResult:
    """What a seed run actually inserted."""

    exercises: int = 0
    tracking: int = 0
    synonyms: int = 0

    def __str__(self) -> str:
        return (
            f"{self.exercises} exercise(s), {self.tracking} tracking row(s), "
            f"{self.synonyms} synonym(s)"
        )


def _assert_catalog_consistent() -> None:
    """Fail loudly on a hand-edit that would corrupt global uniqueness.

    Duplicate slugs or normalized names would break the partial unique indexes,
    and a duplicate synonym across two globals would make global resolution
    permanently ambiguous. Cheaper to catch here than in a constraint violation
    halfway through a run.
    """
    for label, values in (
        ("slug", [item["slug"] for item in PREDEFINED_EXERCISES]),
        ("name", [normalize_name(item["name"]) for item in PREDEFINED_EXERCISES]),
        (
            "synonym",
            [
                normalize_name(text)
                for item in PREDEFINED_EXERCISES
                for text in item.get("synonyms", ())
            ],
        ),
    ):
        duplicates = sorted({v for v in values if values.count(v) > 1})
        if duplicates:
            raise ValueError(f"Duplicate global {label}(s) in seed data: {duplicates}")


def _sync_tracking(db: Session, exercise: Exercise, item: dict) -> int:
    """Add any missing tracking rows for a global exercise. Returns insert count."""
    present = {row.tracking_type for row in exercise.tracking}
    has_primary = any(row.is_primary for row in exercise.tracking)

    wanted: list[tuple[str, bool]] = [(item["primary_tracking"].value, True)]
    wanted += [
        (metric.value, False) for metric in item.get("secondary_tracking", ())
    ]

    inserted = 0
    for value, is_primary in wanted:
        if value in present:
            continue
        if is_primary and has_primary:
            # Changing which metric is primary is a migration's decision.
            continue
        db.add(
            ExerciseTracking(
                exercise_id=exercise.id,
                tracking_type=value,
                is_primary=is_primary,
            )
        )
        present.add(value)
        has_primary = has_primary or is_primary
        inserted += 1
    return inserted


def _sync_synonyms(db: Session, exercise: Exercise, item: dict) -> int:
    """Add any missing synonyms for a global exercise. Returns insert count."""
    present = {row.synonym_normalized for row in exercise.synonyms}

    inserted = 0
    for text in item.get("synonyms", ()):
        display = clean_display_name(text)
        normalized = normalize_name(display)
        if normalized in present:
            continue
        db.add(
            ExerciseSynonym(
                exercise_id=exercise.id,
                synonym=display,
                synonym_normalized=normalized,
                locale=DEFAULT_SYNONYM_LOCALE,
            )
        )
        present.add(normalized)
        inserted += 1
    return inserted


def run_seed(db: Session) -> SeedResult:
    """Upsert the global catalog by slug. Safe to re-run any time."""
    _assert_catalog_consistent()

    existing = {
        exercise.slug: exercise
        for exercise in (
            db.query(Exercise)
            .options(
                selectinload(Exercise.tracking),
                selectinload(Exercise.synonyms),
            )
            .filter(Exercise.user_id.is_(None))
            .all()
        )
    }

    result = SeedResult()
    for item in PREDEFINED_EXERCISES:
        exercise = existing.get(item["slug"])
        if exercise is None:
            display = clean_display_name(item["name"])
            exercise = Exercise(
                user_id=None,
                name=display,
                name_normalized=normalize_name(display),
                slug=item["slug"],
                muscle_group=item.get("muscle_group"),
                is_active=True,
            )
            db.add(exercise)
            # Children reference exercise_id directly, so the id must exist.
            db.flush()
            result.exercises += 1

        result.tracking += _sync_tracking(db, exercise, item)
        result.synonyms += _sync_synonyms(db, exercise, item)

    if result.exercises or result.tracking or result.synonyms:
        db.commit()
    return result
