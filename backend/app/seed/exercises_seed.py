"""Single source of truth for the predefined Exercise catalog.

Edit this list (add/remove exercises) and re-run `python -m scripts.seed_db`
to upsert into the DB.
"""


PREDEFINED_EXERCISES: list[dict[str, str]] = [
    # Chest
    {"name": "Bench Press", "muscle_group": "Chest"},
    {"name": "Incline Dumbbell Press", "muscle_group": "Chest"},
    {"name": "Push Up", "muscle_group": "Chest"},
    # Back
    {"name": "Deadlift", "muscle_group": "Back"},
    {"name": "Pull Up", "muscle_group": "Back"},
    {"name": "Barbell Row", "muscle_group": "Back"},
    {"name": "Lat Pulldown", "muscle_group": "Back"},
    # Legs
    {"name": "Back Squat", "muscle_group": "Legs"},
    {"name": "Front Squat", "muscle_group": "Legs"},
    {"name": "Leg Press", "muscle_group": "Legs"},
    {"name": "Romanian Deadlift", "muscle_group": "Legs"},
    {"name": "Leg Curl", "muscle_group": "Legs"},
    {"name": "Calf Raise", "muscle_group": "Legs"},
    # Shoulders
    {"name": "Overhead Press", "muscle_group": "Shoulders"},
    {"name": "Lateral Raise", "muscle_group": "Shoulders"},
    {"name": "Face Pull", "muscle_group": "Shoulders"},
    # Arms
    {"name": "Barbell Curl", "muscle_group": "Arms"},
    {"name": "Dumbbell Curl", "muscle_group": "Arms"},
    {"name": "Triceps Pushdown", "muscle_group": "Arms"},
    {"name": "Skullcrusher", "muscle_group": "Arms"},
    # Core
    {"name": "Plank", "muscle_group": "Core"},
    {"name": "Hanging Leg Raise", "muscle_group": "Core"},
    {"name": "Cable Crunch", "muscle_group": "Core"},
]
