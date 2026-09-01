"""Single source of truth for the predefined *global* Exercise catalog.

Edit this list and re-run `python -m scripts.seed_db` to upsert into the DB.

Identity is the `slug`, not the name: renaming an exercise here updates nothing
by design, but it also never creates a duplicate, and existing ids survive. The
raw name is no longer the seed key.

`primary_tracking` is stated explicitly for every entry rather than defaulted.
Every one of these movements is a dynamic resistance exercise counted in
repetitions except `plank`, an isometric hold measured in seconds. None of them
is distance-based.

`synonyms` are the common gym shorthand a resolver should accept. They are a
curated starting point, deliberately excluding aliases that name a *different*
movement ("Chin Up" for a pull-up, "Hanging Knee Raise" for a leg raise).
"""

from app.exercises.models import TrackingType


# keys: slug, name, muscle_group, primary_tracking, secondary_tracking, synonyms
PREDEFINED_EXERCISES: list[dict] = [
    # Chest
    {
        "slug": "bench-press",
        "name": "Bench Press",
        "muscle_group": "Chest",
        "primary_tracking": TrackingType.reps,
        "synonyms": ["Bench", "Flat Bench Press"],
    },
    {
        "slug": "incline-dumbbell-press",
        "name": "Incline Dumbbell Press",
        "muscle_group": "Chest",
        "primary_tracking": TrackingType.reps,
        "synonyms": ["Incline DB Press"],
    },
    {
        "slug": "push-up",
        "name": "Push Up",
        "muscle_group": "Chest",
        "primary_tracking": TrackingType.reps,
        "synonyms": ["Pushup", "Press Up"],
    },
    # Back
    {
        "slug": "deadlift",
        "name": "Deadlift",
        "muscle_group": "Back",
        "primary_tracking": TrackingType.reps,
        "synonyms": ["Conventional Deadlift"],
    },
    {
        "slug": "pull-up",
        "name": "Pull Up",
        "muscle_group": "Back",
        "primary_tracking": TrackingType.reps,
        "synonyms": ["Pullup"],
    },
    {
        "slug": "barbell-row",
        "name": "Barbell Row",
        "muscle_group": "Back",
        "primary_tracking": TrackingType.reps,
        "synonyms": ["Bent Over Row", "BB Row"],
    },
    {
        "slug": "lat-pulldown",
        "name": "Lat Pulldown",
        "muscle_group": "Back",
        "primary_tracking": TrackingType.reps,
        "synonyms": ["Pulldown"],
    },
    # Legs
    {
        "slug": "back-squat",
        "name": "Back Squat",
        "muscle_group": "Legs",
        "primary_tracking": TrackingType.reps,
        "synonyms": ["Squat", "Barbell Squat"],
    },
    {
        "slug": "front-squat",
        "name": "Front Squat",
        "muscle_group": "Legs",
        "primary_tracking": TrackingType.reps,
    },
    {
        "slug": "leg-press",
        "name": "Leg Press",
        "muscle_group": "Legs",
        "primary_tracking": TrackingType.reps,
    },
    {
        "slug": "romanian-deadlift",
        "name": "Romanian Deadlift",
        "muscle_group": "Legs",
        "primary_tracking": TrackingType.reps,
        "synonyms": ["RDL"],
    },
    {
        "slug": "leg-curl",
        "name": "Leg Curl",
        "muscle_group": "Legs",
        "primary_tracking": TrackingType.reps,
        "synonyms": ["Hamstring Curl"],
    },
    {
        "slug": "calf-raise",
        "name": "Calf Raise",
        "muscle_group": "Legs",
        "primary_tracking": TrackingType.reps,
    },
    # Shoulders
    {
        "slug": "overhead-press",
        "name": "Overhead Press",
        "muscle_group": "Shoulders",
        "primary_tracking": TrackingType.reps,
        "synonyms": ["OHP", "Shoulder Press", "Military Press"],
    },
    {
        "slug": "lateral-raise",
        "name": "Lateral Raise",
        "muscle_group": "Shoulders",
        "primary_tracking": TrackingType.reps,
        "synonyms": ["Side Raise"],
    },
    {
        "slug": "face-pull",
        "name": "Face Pull",
        "muscle_group": "Shoulders",
        "primary_tracking": TrackingType.reps,
    },
    # Arms
    {
        "slug": "barbell-curl",
        "name": "Barbell Curl",
        "muscle_group": "Arms",
        "primary_tracking": TrackingType.reps,
        "synonyms": ["BB Curl"],
    },
    {
        "slug": "dumbbell-curl",
        "name": "Dumbbell Curl",
        "muscle_group": "Arms",
        "primary_tracking": TrackingType.reps,
        "synonyms": ["DB Curl"],
    },
    {
        "slug": "triceps-pushdown",
        "name": "Triceps Pushdown",
        "muscle_group": "Arms",
        "primary_tracking": TrackingType.reps,
        "synonyms": ["Tricep Pushdown", "Cable Pushdown"],
    },
    {
        "slug": "skullcrusher",
        "name": "Skullcrusher",
        "muscle_group": "Arms",
        "primary_tracking": TrackingType.reps,
        "synonyms": ["Skull Crusher", "Lying Triceps Extension"],
    },
    # Core
    {
        "slug": "plank",
        "name": "Plank",
        "muscle_group": "Core",
        # Isometric hold: measured in seconds, not repetitions.
        "primary_tracking": TrackingType.duration,
        "synonyms": ["Front Plank"],
    },
    {
        "slug": "hanging-leg-raise",
        "name": "Hanging Leg Raise",
        "muscle_group": "Core",
        "primary_tracking": TrackingType.reps,
    },
    {
        "slug": "cable-crunch",
        "name": "Cable Crunch",
        "muscle_group": "Core",
        "primary_tracking": TrackingType.reps,
        "synonyms": ["Kneeling Cable Crunch"],
    },
]
