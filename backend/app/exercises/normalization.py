"""Name normalization and slug derivation for the Exercise domain.

Normalization is deliberately application-layer and mechanical: trim, lowercase,
collapse runs of whitespace. No stemming, lemmatization or NLP -- the normalized
value is a *persisted* column that uniqueness indexes and the name/synonym
resolver both rely on, so it has to stay stable and cheap to reproduce.

The same rules apply to `Exercise.name_normalized` and
`ExerciseSynonym.synonym_normalized`.

Alembic migrations intentionally inline a copy of `normalize_name` /
`slugify_name` instead of importing them: a migration must keep producing the
same values it produced the day it was written, even if these helpers evolve.
"""

import re


_WHITESPACE_RUN = re.compile(r"\s+")
_NON_SLUG_RUN = re.compile(r"[^a-z0-9]+")


def clean_display_name(value: str) -> str:
    """Tidy a name for storage in the display column, preserving its casing.

    >>> clean_display_name("  Incline   Bench Press ")
    'Incline Bench Press'
    """
    return _WHITESPACE_RUN.sub(" ", value).strip()


def normalize_name(value: str) -> str:
    """Return the canonical comparison form of an exercise or synonym name.

    >>> normalize_name("  Incline   Bench Press ")
    'incline bench press'
    """
    return clean_display_name(value).lower()


def slugify_name(value: str) -> str:
    """Derive a URL/seed-safe slug from a name.

    Only used for global exercises; personal exercises keep `slug = NULL` and
    are identified by `Exercise.id`.

    >>> slugify_name("Romanian Deadlift")
    'romanian-deadlift'
    """
    return _NON_SLUG_RUN.sub("-", normalize_name(value)).strip("-")
