# AI HANDOFF — Gym Tracker

> **Purpose of this file.** This is the permanent, self-contained context document for any AI coding
> agent joining this project with **zero** access to previous conversations. It records what is
> *actually implemented today*, the *locked* domain decisions that must not be re-litigated, the known
> technical debt, and the exact next task.
>
> **Branch:** `main` · **Last verified:** 2026-09-01
>
> **Project state:** **Phase 1 — Alembic Foundation: COMPLETED** (§2.9) ·
> **Phase 2 — Exercise Domain: COMPLETED** (§2.10).
> Alembic owns schema evolution: baseline **`f3f47238398b`**, head **`da9c526717c0`**.
> Exercises now support global vs. personal ownership, normalized names, global slugs, relational
> tracking metadata, synonyms, and soft archiving. Existing data preserved (9 / 23 / 8 / 17 / 58).
> **Next task: Phase 3 — Set & Tracking** (§7).
>
> This document deliberately records **no commit hash**. Git is the source of truth for revision
> history — run `git log`/`git status` if you need it. Describe state semantically here so this file
> does not need editing after every commit.
>
> **Reading rules for the next agent:**
> 1. Section 2 (implementation state) describes reality. Section 4 (locked decisions) describes the
>    agreed *target* design. Do not confuse the two.
> 2. Anything in Section 4 is **decided**. Implement it; do not redesign it.
> 3. Section 9 lists things that are explicitly out of scope right now.
> 4. Several `TODO` comments in the codebase predate the locked decisions and are **wrong**. See §5.

---

# 1. PROJECT OVERVIEW

## Purpose

Gym Tracker is a **mobile-first personal gym training tracker**. A user logs in, picks exercises from
a catalog, and records what they actually performed (sets, reps, load). The long-term goal is to also
manage reusable **workout templates** (planned intent) separately from **workout sessions**
(actual performance), and eventually add an AI/voice logging layer.

Primary target device: **Galaxy S21-class phone** (mobile-first, not desktop-first). Dark mode is a
first-class concern.

## Current backend stack

| Concern | Choice |
|---|---|
| Language | **Python 3.13.2** (venv at `backend/.venv`) |
| Framework | FastAPI 0.115.0 |
| ORM | SQLAlchemy 2.0.35, **legacy `Column(...)` declarative style** (not `Mapped[]`/`mapped_column`) |
| Validation | Pydantic 2.9.2 + `pydantic-settings` 2.5.2 |
| Auth | JWT bearer HS256 via `python-jose`; password hashing via `passlib[bcrypt]` with **`bcrypt` pinned to 4.0.1** (passlib 1.7.4 breaks on bcrypt ≥ 4.1 — do not bump it casually; the reason is documented in `requirements.txt`) |
| Server | uvicorn 0.30.6 |
| Migrations | **Alembic 1.13.3** — baseline `f3f47238398b`, head `da9c526717c0`; `create_all()` removed from startup (see §2.9, §2.10) |
| Tests | **NONE** (no test files, no pytest/httpx in `requirements.txt`) |

## Current frontend stack

| Concern | Choice |
|---|---|
| Framework | React 18.3.1 + Vite 5.4.8 |
| Language | **JavaScript / JSX only — no TypeScript** |
| Styling | TailwindCSS 3.4.13 (+ `tailwindcss-animate`) with shadcn-style CSS variables (`frontend/src/styles/global.css`) |
| Components | Hand-rolled primitives in shadcn *style*; the shadcn CLI is **not** installed. Icons via `lucide-react` |
| Routing | `react-router-dom` 6.26.2 |
| Forms | React Hook Form 7.53 + Zod 3.23 |
| HTTP | Axios 1.7, single client with interceptors |
| State | React Context (`AuthContext`, `ThemeContext`) |
| Path alias | `@` → `frontend/src` (configured in both `vite.config.js` and `jsconfig.json`) |

## Current database

**SQLite**, file `backend/gym.db` (git-ignored, **contains real data** — see §6).
`DATABASE_URL` is configurable; `Settings.is_sqlite` exists so a future PostgreSQL swap needs only an
env change. Nothing PostgreSQL-specific is in use today.

## Main architectural structure

**Modular monolith.** Backend is split by domain module, each module holding its own
`models / schemas / service / routes`:

```
backend/
  alembic.ini          # Alembic config; sqlalchemy.url intentionally blank
  alembic/             # migration environment
    env.py             # reads DATABASE_URL from app settings; target_metadata = Base.metadata
    versions/          # f3f47238398b (baseline) -> da9c526717c0 (exercise domain)
  scripts/seed_db.py   # CLI seeding entrypoint (NOT under app/)
  app/
    main.py            # app factory: CORS, model imports, router mounting (no create_all)
    core/              # config, database, dependencies, exceptions, response envelope, security
    auth/              # User model, register/login/me
    exercises/         # Exercise + ExerciseTracking + ExerciseSynonym, normalization, read+write API
    workouts/          # Workout + WorkoutExercise + Set
    seed/              # global exercise catalog + idempotent slug-keyed seeder
```

Hard rules already followed by the codebase:

- `service.py` contains business logic and **never imports FastAPI primitives**.
- `routes.py` is thin: dependency injection + call service + wrap in response envelope.
- Every API response is wrapped as `{ "success": bool, "data": any, "error": str|null }` via
  `app/core/response.py` and the global exception handlers in `app/core/exceptions.py`.
- All routers are mounted under `/api`.

---

# 2. CURRENT IMPLEMENTATION STATE

> Everything in this section was **verified against the repository after Phase 1 completed**.
> **Planned functionality is marked explicitly and is NOT implemented.**

## 2.1 Authentication — IMPLEMENTED

- `POST /api/auth/register` → creates user, 201, returns `UserOut`.
- `POST /api/auth/login` → returns `{ access_token, token_type }`.
- `GET /api/auth/me` → returns current user, requires bearer token.
- Password hashing via passlib/bcrypt; JWT signed HS256 with `sub = user.id`, expiry from
  `JWT_EXPIRE_MINUTES` (default 60).
- `app/core/dependencies.py::get_current_user` resolves the bearer token to a `User`.
- Every workouts/exercises endpoint requires authentication.
- Ownership is enforced in the service layer: all workout queries filter by `user_id`, and a workout
  belonging to another user raises `NotFoundError` (deliberately not `403`, to avoid leaking existence).

**NOT implemented:** refresh tokens, logout server-side/token revocation, password reset, email
verification, roles/permissions, rate limiting.

## 2.2 Exercises — IMPLEMENTED (Phase 2)

The exercise domain from §4.5 is implemented. Full delivery detail is in **§2.10**; this is the
behavioral summary.

- **Ownership.** `Exercise.user_id IS NULL` = global (visible to every authenticated user);
  `user_id = <owner>` = personal (visible only to its owner). Global exercises carry a stable unique
  `slug`; personal ones have `slug = NULL` and are identified by `Exercise.id`.
- **`GET /api/exercises`** returns *active globals + the caller's active personal exercises*, ordered
  by `muscle_group, name` with unclassified (NULL muscle group) entries last. It never exposes
  another user's exercises. Still no pagination, search, or filters.
- **Write endpoints (personal only):** `POST /api/exercises`,
  `PATCH /api/exercises/{id}`, `POST /api/exercises/{id}/archive`. There is **no DELETE** — archiving
  is a soft state change. Editing or archiving a *global* exercise is rejected with a 422.
- **Minimum creation payload = `name` + `primary_tracking_type`.** `muscle_group` is nullable, and
  `secondary_tracking_types` / `synonyms` are optional.
- **Tracking is relational** (`exercise_tracking`): exactly one primary metric and zero or more
  secondaries per exercise, drawn from `reps | duration | distance`. **Weight is not a tracking
  type.**
- **Normalized names.** `name_normalized` is persisted (trim → lowercase → collapse whitespace runs).
  The display `name` is stored whitespace-collapsed but case-preserving.
- **Uniqueness.** A user cannot have two personal exercises with the same normalized name (409).
  Different users may reuse the same normalized name, and a personal name may reuse a global one.
  The old globally-unique raw-name index is gone.
- **Synonyms** (`exercise_synonyms`) with the same normalization. A personal synonym may reuse a
  global synonym's text.
- **Resolver** (`service.resolve_exercise`, service-layer only, **no HTTP endpoint yet**): personal
  exact name → personal synonym → global exact name → global synonym. Several candidates at the same
  level return an *ambiguous* result rather than an arbitrary pick.
- **Tracking freeze.** Personal tracking is editable until the exercise has at least one persisted
  Set (via `Exercise → WorkoutExercise → Set`); afterwards a tracking *change* is rejected while name
  and metadata stay editable. Re-sending an unchanged tracking configuration is not a change.
- **Archiving** sets `is_active = False`. The row stays in the database, historical
  `WorkoutExercise` rows keep resolving and are never rewritten, and the exercise disappears from
  listings and can no longer be added to a workout. Idempotent; no restore endpoint, no UI.
- **Seeding** is keyed by `slug`, not `name`, and only ever inserts what is missing (§2.10). The
  current DB catalog is 23 global rows across 6 muscle groups (Legs 6, Arms 4, Back 4, Chest 3,
  Core 3, Shoulders 3) with 23 tracking rows and 26 seeded synonyms.

**NOT implemented:** equipment, movement pattern, exercise type, difficulty, multiple muscle groups,
media/images, restore endpoint, exercise search/filter endpoints, an HTTP resolver endpoint, locale
handling beyond storing `locale` (everything is seeded as `en` and resolution ignores it), and any
exercise UI beyond the compatibility guard in §2.10.

## 2.3 Workouts / Sessions — IMPLEMENTED AS A SINGLE "WORKOUT" ENTITY

There is **no Template/Session split today**. There is one entity, `Workout`, which represents a
dated, performed workout owned by a user.

Endpoints (all auth-scoped to the current user):

| Method | Path | Behavior |
|---|---|---|
| GET | `/api/workouts` | list, ordered `date DESC, created_at DESC`, no nested tree, no pagination |
| POST | `/api/workouts` | create with optional nested exercises + sets, 201 |
| GET | `/api/workouts/{id}` | full nested detail, eager-loaded via `selectinload` |
| PUT | `/api/workouts/{id}` | **full replace** of scalars *and* the whole nested tree |
| DELETE | `/api/workouts/{id}` | deletes workout + cascade children, returns 200 with `data: null` |

Implementation notes that matter:

- `get_workout` uses `selectinload` for `exercises` → `exercise` and `exercises` → `sets`, so the
  detail read is a small fixed number of queries (no N+1).
- `_validate_exercise_ids(db, user_id, ids)` batch-validates all referenced `exercise_id`s in one
  query and raises `ValidationError` listing the rejected ids. Since Phase 2 it is **ownership- and
  archive-aware**: an id is valid only if the exercise is active *and* either global or owned by the
  caller. Another user's exercise, an archived exercise and a nonexistent id are all reported
  identically as "Unknown exercise_id(s)", so the error never confirms that someone else's exercise
  exists. Reads (`get_workout`) deliberately do **not** filter, so history stays readable.
- `order_index` is optional in the payload and falls back to the array position.
- **`update_workout` reassigns `workout.exercises`**, which triggers `delete-orphan` cascade. This
  **destroys and recreates all `WorkoutExercise` and `Set` rows with new primary keys** on every PUT.
  This is confirmed by the live DB: 17 `workout_exercises` rows but `max(id) = 32`; 58 `sets` rows but
  `max(id) = 98`. See §5.

**NOT implemented:** templates, session start/end timestamps, active vs. completed state, notes,
per-session duration, granular child-resource endpoints, pagination.

## 2.4 Sets — IMPLEMENTED, REPS+WEIGHT ONLY

- `Set` has: `id`, `workout_exercise_id`, `reps` (INTEGER **NOT NULL**), `weight`
  (FLOAT **NOT NULL**), `order_index`.
- Validation: `reps > 0`, `weight >= 0` (Pydantic `SetIn`, mirrored by Zod `setSchema` on the frontend).
- Sets only exist as part of the nested workout tree. **There are no `/sets` endpoints in the backend.**

**NOT implemented:** nullable weight, duration, distance, tracking types, RPE, RIR, set types
(warmup/working/dropset), decimal weight precision, any standalone set endpoint.

## 2.5 Frontend pages / features — IMPLEMENTED

Routing (`src/routes/AppRoutes.jsx`, with `ProtectedRoute` / `PublicRoute` guards):

| Route | Page | Notes |
|---|---|---|
| `/login` | `LoginPage` | public-only; authenticated users are redirected to `/home` |
| `/register` | `RegisterPage` | public-only |
| `/` | — | protected; **redirects to `/home`** (`<Route index>` → `<Navigate to="/home" replace />`) |
| `/home` | `HomePage` | protected — this is the real home route, **not** `/` |
| `/workouts/new` | `WorkoutEditorPage` | protected, create mode |
| `/workouts/:id` | `WorkoutDetailPage` | protected |
| `/workouts/:id/edit` | `WorkoutEditorPage` | protected, edit mode |
| `*` | `NotFoundPage` | |

Working features:

- **Auth flow**: `AuthContext` with `login/register/logout`, hydration from `/auth/me`, token in
  `localStorage` (`src/utils/storage.js`), global `401` handling — the Axios response interceptor
  clears the token and dispatches an `auth:unauthorized` window event that `AuthContext` listens to.
- **Response unwrapping**: the Axios interceptor unwraps `{success,data,error}` so API modules return
  `data` directly and throw `Error(error)` on failure.
- **Theme system**: system / light / dark with `localStorage` persistence and an anti-FOUC inline
  script in `index.html`; `ThemeToggle` in the header.
- **Layout**: `AppShell` + `Header` + `BottomNav`, mobile-first with safe-area padding.
- **Workout list**: `WorkoutList` / `WorkoutCard` on `HomePage`.
- **Workout editor**: `WorkoutForm` (RHF + Zod) with nested field arrays — exercises
  (`ExerciseFieldCard`) each containing sets (`SetRow`), plus `ExercisePicker` (search + grouped by
  `muscle_group`) in a `Modal`.
- **Workout detail**: renders exercises and sets, formatted as `reps · kg`.
- **UI primitives**: `AppButton`, `AppInput`, `AuthCard`, `PageContainer`, `LoadingScreen`,
  `StatusView` (empty/error states), `Modal`, `Label`.
- **Hooks**: `useAuth`, `useTheme`, `useAsync`, `useRestTimer`.

**NOT implemented / not wired:** rest timer UI (component exists but is imported by nothing —
see §2.8), templates UI, exercise creation UI, statistics/charts, profile/settings page, offline
support, PWA, i18n framework (some Italian strings are hardcoded).

## 2.6 API structure — CURRENT SURFACE

```
GET    /api/health
POST   /api/auth/register
POST   /api/auth/login
GET    /api/auth/me
GET    /api/exercises
POST   /api/exercises
PATCH  /api/exercises/{exercise_id}
POST   /api/exercises/{exercise_id}/archive
GET    /api/workouts
POST   /api/workouts
GET    /api/workouts/{workout_id}
PUT    /api/workouts/{workout_id}
DELETE /api/workouts/{workout_id}
```

That is the complete list. All responses use the `{success, data, error}` envelope.
Interactive docs: `http://localhost:8000/docs`.

## 2.7 Tests — NONE

There are **zero** test files in the repository, and `pytest` / `httpx` are not in
`backend/requirements.txt`. There is no CI configuration. All verification so far has been manual
(Swagger UI, browser, ad-hoc scripts). Phase 1 and Phase 2 verification was likewise manual, using
throwaway scratch databases and temporary scripts that were **deleted afterwards** — nothing was
left in the repository. Phase 2's checks are enumerated in §2.10 so a future agent knows what was
actually covered.

Note for whoever builds the real suite: `httpx` is **not installed**, so
`fastapi.testclient.TestClient` does not work today. Phase 2's HTTP checks ran against a real
`uvicorn` process using stdlib `urllib`.

## 2.8 Known inconsistencies (verified)

1. **`/sets` endpoints are documented and called but do not exist.** `api_contract.md` lists
   `POST /sets`, `PUT /sets/{id}`, `DELETE /sets/{id}`, and `frontend/src/api/sets.js` exports
   `createSet/updateSet/deleteSet` hitting those paths. The backend implements none of them. The
   frontend module is currently **dead code** (imported by no component), so it does not break the
   app — it would 404 if used.
2. **`PRD.md` lists "programs or templates" as a non-goal**, which directly contradicts the locked
   decision that Templates are a core entity (§4). The locked decisions win.
3. **`architecture.md` schema is stale**: it shows `WorkoutExercise` without `order_index`, which
   exists in both the model and the live DB.
4. **`docs/project-status.md` is stale**: it declares the current phase to be "Phase 5 Step 3
   (Rest Timer, UX Polish, Empty States, Loading Skeletons)". Empty/error states are already
   implemented (`StatusView`), Phases 1 (Alembic) and 2 (Exercise domain) are now **complete**, and
   the real next task is **Phase 3 — Set & Tracking** (§7).
   ⚠️ **Phase-numbering collision:** the old frontend-era numbering ("Phase 5 Step 3") is unrelated to
   the new domain roadmap numbering in §8. Use §8 numbering from now on.
5. **`docs/decision-log.md` is empty (0 bytes)** despite being the designated place for decisions.
   This handoff document is currently the only durable record.
6. **`RestTimer.jsx` is orphaned and would render unstyled.** It is imported by no page, and it uses
   legacy BEM class names (`rest-timer`, `rest-timer__display`, `btn`, `btn--ghost`) that no longer
   exist since the stylesheet was rewritten for Tailwind.
7. **Orphaned legacy UI primitives**: `frontend/src/components/ui/Button.jsx` and
   `frontend/src/components/ui/Input.jsx` are imported by nothing (superseded by `AppButton` /
   `AppInput`) and also reference removed CSS classes.
8. **Two different workout-date defaults** exist in the backend — `Workout.date` model default uses
   `datetime.utcnow().date()` while `create_workout` uses `date.today()` (server-local). See §5.
9. **`datetime.utcnow()` is used for `created_at` defaults**, which is deprecated in Python 3.12+.
   `app/core/security.py` already uses the correct `datetime.now(timezone.utc)`.
10. **The ORM class is named `Set`** (`app/workouts/models.py`), which shadows the meaning of the
    Python builtin `set` in that module; `service.py` works around it by using `set[int]` annotations
    carefully. Be careful when importing.

## 2.9 Migrations — IMPLEMENTED (Phase 1, COMPLETED)

**Alembic 1.13.3 is installed, configured, and owns schema evolution.** This phase was
infrastructure only: no column was added, renamed, retyped, or dropped, and no domain behavior
changed.

### What exists

- `backend/alembic.ini` — `sqlalchemy.url` is **intentionally left blank**.
- `backend/alembic/env.py` — resolves the URL from `app.core.config.Settings.database_url` (the same
  `DATABASE_URL` / `.env` the application reads), so Alembic and the app can never point at
  different databases. `target_metadata = Base.metadata`, with **all three** model modules imported
  so autogenerate sees the complete schema. `render_as_batch` is enabled **only for SQLite** (needed
  for the Phase 3 type/nullability changes) and switches itself off for PostgreSQL. An
  `-x db_url=...` override exists for running migrations against throwaway databases.
- `backend/alembic/versions/f3f47238398b_baseline_existing_schema.py` — the baseline revision,
  `down_revision = None`.

### Baseline and stamping

- **Baseline revision: `f3f47238398b`** ("baseline existing schema").
- It was generated by autogenerating against an **empty scratch database**, because autogenerating
  against the populated `gym.db` would have produced an empty migration.
- Applying it to an empty database reproduces the §3 schema exactly. This was verified two
  independent ways across all 17 schema objects: a normalized textual DDL diff, and a structural
  diff of `pragma table_info` / `foreign_key_list` / `index_list` (columns, types, nullability,
  primary keys, both `ON DELETE CASCADE` FKs, the `ON DELETE RESTRICT` FK, all 13 indexes, and the
  unique flags on `ix_users_email` / `ix_exercises_name`).
- **`backend/gym.db` was preserved.** The existing populated database was **`stamp`ed** at the
  baseline, **not upgraded through it** — `alembic stamp head` only wrote the `alembic_version` row
  and executed no DDL. `alembic upgrade head` against it is now a verified no-op.
- A timestamped backup was taken first: `backend/gym.db.backup-20260830-225004` (73,728 bytes).
  `backend/.gitignore` now also ignores `*.db.backup-*`, because the pre-existing `*.db` rule did
  **not** cover it and these snapshots contain real user data.
- **`alembic current` and `alembic heads` were aligned** at `f3f47238398b (head)` at the end of this
  phase — a single head, no branches. (The head is now `da9c526717c0`; see §2.10.)

### Row counts after Phase 1 (unchanged)

| Table | Rows |
|---|---|
| `users` | **9** |
| `exercises` | **23** |
| `workouts` | **8** |
| `workout_exercises` | **17** |
| `sets` | **58** |

A row-level comparison against the pre-migration backup confirmed **every row is identical**. The
only change to the database file is the added `alembic_version` table (§3).

### How `create_all()` was retired

- **`Base.metadata.create_all()` has been removed from application startup** (`app/main.py`). The
  now-unused `Base, engine` import was dropped with it. The model-module imports remain, because
  they register the mappers the routers need.
- **`backend/start.bat` and the Docker `CMD` run `alembic upgrade head` before serving.** Both are
  no-ops when the database is already current; `start.bat` refuses to start the server if the
  migration fails. This preserves the previous "just works" behavior now that the app no longer
  creates tables itself.
- **`scripts/seed_db.py` requires an already-migrated schema.** It no longer calls `create_all()`;
  instead it checks that a table exists and exits with a "run `alembic upgrade head` first"
  instruction rather than a raw `OperationalError`. Phase 2 pointed that check at the *newest* table
  (`exercise_tracking`) so a database stalled at an older revision is caught too, not just an empty
  one.

### ⚠️ The baseline `downgrade()` is destructive

`downgrade()` on `f3f47238398b` **drops every table**, which against the real populated
`backend/gym.db` is total, unrecoverable data loss. It exists only so the revision is reversible on
throwaway databases. **Never run it against the real `gym.db`.** This is noted in the revision's own
docstring as well.

### Verified after Phase 1

`alembic current`/`heads`/`check`; row counts and row-level data vs. the backup; `pragma
foreign_key_check` still clean; FastAPI boots without `create_all`; `/api/health` returns the
envelope; `/api/exercises` and `/api/workouts` still return 401 unauthenticated; the API surface was
still exactly seven routes (Phase 2 later added three — §2.6); `start.bat` migrates then serves. A
full CRUD round trip
(register → login → `/auth/me` → exercises → create → nested detail → list → PUT → 404 path →
422 unknown `exercise_id` → delete) was run against a database built **purely by Alembic**, which
also proves the fresh-install path works without `create_all()`.

## 2.10 Exercise domain — IMPLEMENTED (Phase 2, COMPLETED)

**Migration revision: `da9c526717c0`** ("exercise domain foundation"),
`down_revision = "f3f47238398b"`. This is the first revision that changes the domain schema.
Behavioral summary is in §2.2; the resulting schema is in §3.

### Files

Created:

- `backend/app/exercises/normalization.py` — `clean_display_name`, `normalize_name`, `slugify_name`.
- `backend/alembic/versions/da9c526717c0_exercise_domain_foundation.py`.

Modified: `app/exercises/{models,schemas,service,routes}.py`,
`app/seed/{exercises_seed,seeder}.py`, `app/workouts/{service,schemas}.py`, `scripts/seed_db.py`,
and one line of `frontend/src/components/workouts/ExercisePicker.jsx` (see *Frontend guard* below).

### Migration of the existing 23 exercises

All 23 rows **kept their ids** and became global (`user_id = NULL`, `is_active = 1`), with
`name_normalized` and `slug` derived from the stored name by rules inlined in the migration (a frozen
copy of `normalization.py`, so the revision keeps producing the values it produced when written).

Primary tracking was **not inferred**. The migration carries an explicit `slug → metric` table and
raises rather than defaulting if a slug is missing from it. Every one of the 23 is a dynamic
resistance movement counted in repetitions except **`plank`, which is `duration`** (isometric hold).
None is distance-based, and none was ambiguous, so no stop condition was triggered. The same explicit
mapping lives in `app/seed/exercises_seed.py`.

`exercises` is rebuilt twice by `batch_alter_table`: once to add the nullable columns and relax
`muscle_group`, then — after the backfill — once more to tighten `name_normalized` / `is_active` to
NOT NULL and add the slug-scope CHECK, which can only hold once slugs exist. Both rebuilds copy `id`
explicitly, and `workout_exercises.exercise_id` plus its `ON DELETE RESTRICT` FK survived intact.

### SQLite specifics worth knowing

- **Uniqueness needs partial indexes, not plain UNIQUE.** SQLite treats NULLs as distinct, so
  `UNIQUE(user_id, name_normalized)` alone would let every global row collide freely. The scopes get
  one partial index each (§3), which is also exactly what allows a personal name to reuse a global
  one.
- **Verified on SQLAlchemy 2.0 / SQLite 3.45:** a `batch_alter_table` rebuild *does* reflect and
  re-emit both CHECK constraints and partial-index WHERE clauses, so a later migration inherits them
  for free. The flip side, found the hard way while testing `downgrade()`: a batch operation that
  drops `user_id` or `slug` must **drop `ck_exercises_slug_scope` first**, or the rebuild re-emits a
  constraint referencing columns that no longer exist.
- `downgrade()` **refuses to run while any personal exercise exists**, since it owns the column that
  makes them addressable and neither deleting nor promoting them is a migration's call to make
  silently. With globals only it restores the baseline schema exactly (verified).

### Seeder behavior

`run_seed` now identifies global exercises **by `slug`**, not by name, and returns a `SeedResult`
(`exercises` / `tracking` / `synonyms` inserted). It only ever *adds what is missing*: an existing
global's name, muscle group or primary tracking is treated as data a migration owns, not seed state
to overwrite. It reads only `user_id IS NULL` rows, so personal exercises are never touched or
promoted. A `_assert_catalog_consistent()` pre-check fails loudly on duplicate slugs, normalized
names or synonyms in the hand-edited catalog.

Observed: on a fresh Alembic-built database, `23 exercises / 23 tracking / 26 synonyms`; against the
already-migrated `gym.db`, `0 / 0 / 26` (the migration had already created tracking); every
subsequent run `0 / 0 / 0`.

### Frontend guard (the one allowed exception)

`ExercisePicker.jsx` searched with `ex.muscle_group.toLowerCase()`, which would throw as soon as a
personal exercise had no muscle group. Changed to `(ex.muscle_group || '').toLowerCase()` — one line.
**Nothing else in the frontend was touched**; real frontend adaptation is Phase 6.

### Verification performed

Data safety on the real `gym.db`, before and after seeding, against the pre-migration backup: row
counts (9 / 23 / 8 / 17 / 58); **byte-identical** `id` sets and full-row comparisons for `users`,
`workouts`, `workout_exercises`, `sets`, and the pre-existing `exercises` columns; all 23 global,
active, correctly normalized and slugged with no collisions; exactly one primary tracking row each;
`plank = duration` and every other primary `reps`; all 17 `workout_exercises` still joining;
`pragma foreign_key_check` and `pragma integrity_check` clean; `alembic current` = `heads` =
`da9c526717c0`; `alembic check` clean. The same suite passed first on a **copy** of `gym.db` before
the real run.

Behavioral checks (57 assertions at the service layer + 29 over HTTP, all on scratch databases):
globals visible; personal creation with name + primary tracking only; cross-user invisibility;
same-user duplicate normalized name rejected (`"My Press"` vs `"  my   press "` → 409); different
user may reuse it; personal name may overlap a global; personal synonym may overlap a global synonym;
all four resolver priority levels plus the ambiguity path (forced by inserting a duplicate synonym
directly, since the service prevents it); tracking editable before the first Set and rejected after;
archive hides the exercise, is idempotent, keeps the row, blocks new workouts, and leaves history
readable; another user's exercise not addable; seed idempotency; and full workout CRUD
(create/list/get/PUT/delete + cross-user 404). Also confirmed: `weight` is rejected as a tracking
type, a metric cannot be both primary and secondary, `DELETE /api/exercises/{id}` is a 405, and
editing a global is a 422.

---

# 3. CURRENT DATABASE SCHEMA

This is the **exact live schema** of `backend/gym.db`, dumped from `sqlite_master` on 2026-09-01,
i.e. at revision `da9c526717c0`. `users`, `workouts`, `workout_exercises` and `sets` are still
byte-for-byte what `create_all()` produced and the baseline reproduces; **`exercises` was widened and
two tables were added by Phase 2** (§2.10). `alembic_version` is listed at the end.

Formatting note: SQLite quotes the table name (`CREATE TABLE "exercises"`) after a
`batch_alter_table` rebuild. That is cosmetic.

```sql
CREATE TABLE users (
    id              INTEGER NOT NULL,
    email           VARCHAR(255) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    created_at      DATETIME NOT NULL,
    PRIMARY KEY (id)
);
CREATE UNIQUE INDEX ix_users_email ON users (email);
CREATE INDEX ix_users_id ON users (id);

CREATE TABLE "exercises" (
    id              INTEGER NOT NULL,
    name            VARCHAR(120) NOT NULL,
    muscle_group    VARCHAR(60),              -- nullable since Phase 2
    created_at      DATETIME NOT NULL,
    user_id         INTEGER,                  -- NULL = global, else the owner
    name_normalized VARCHAR(120) NOT NULL,
    slug            VARCHAR(140),             -- required for globals, NULL for personal
    is_active       BOOLEAN NOT NULL,         -- soft archive flag
    PRIMARY KEY (id),
    CONSTRAINT fk_exercises_user_id_users
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    CONSTRAINT ck_exercises_slug_scope CHECK (
        (user_id IS NULL AND slug IS NOT NULL) OR (user_id IS NOT NULL AND slug IS NULL)
    )
);
CREATE INDEX ix_exercises_id ON exercises (id);
CREATE INDEX ix_exercises_muscle_group ON exercises (muscle_group);
CREATE INDEX ix_exercises_name ON exercises (name);              -- no longer UNIQUE
CREATE INDEX ix_exercises_name_normalized ON exercises (name_normalized);
CREATE INDEX ix_exercises_user_id ON exercises (user_id);
-- Partial unique indexes: see §2.10 for why plain UNIQUE cannot express this on SQLite.
CREATE UNIQUE INDEX uq_exercises_global_name_normalized
    ON exercises (name_normalized) WHERE user_id IS NULL;
CREATE UNIQUE INDEX uq_exercises_global_slug
    ON exercises (slug) WHERE user_id IS NULL;
CREATE UNIQUE INDEX uq_exercises_personal_name_normalized
    ON exercises (user_id, name_normalized) WHERE user_id IS NOT NULL;

CREATE TABLE exercise_tracking (
    id            INTEGER NOT NULL,
    exercise_id   INTEGER NOT NULL,
    tracking_type VARCHAR(16) NOT NULL,
    is_primary    BOOLEAN NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT ck_exercise_tracking_type
        CHECK (tracking_type IN ('reps', 'duration', 'distance')),
    FOREIGN KEY (exercise_id) REFERENCES exercises (id) ON DELETE CASCADE,
    CONSTRAINT uq_exercise_tracking_type UNIQUE (exercise_id, tracking_type)
);
CREATE INDEX ix_exercise_tracking_exercise_id ON exercise_tracking (exercise_id);
CREATE INDEX ix_exercise_tracking_id ON exercise_tracking (id);
-- "At most one primary per exercise". "At least one" has no declarative form in
-- SQLite and is enforced by the service layer + the Phase 2 backfill.
CREATE UNIQUE INDEX uq_exercise_tracking_primary
    ON exercise_tracking (exercise_id) WHERE is_primary = 1;

CREATE TABLE exercise_synonyms (
    id                 INTEGER NOT NULL,
    exercise_id        INTEGER NOT NULL,
    synonym            VARCHAR(120) NOT NULL,
    synonym_normalized VARCHAR(120) NOT NULL,
    locale             VARCHAR(10) NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (exercise_id) REFERENCES exercises (id) ON DELETE CASCADE,
    CONSTRAINT uq_exercise_synonyms_scope
        UNIQUE (exercise_id, locale, synonym_normalized)
);
CREATE INDEX ix_exercise_synonyms_exercise_id ON exercise_synonyms (exercise_id);
CREATE INDEX ix_exercise_synonyms_id ON exercise_synonyms (id);
CREATE INDEX ix_exercise_synonyms_synonym_normalized
    ON exercise_synonyms (synonym_normalized);

CREATE TABLE workouts (
    id         INTEGER NOT NULL,
    user_id    INTEGER NOT NULL,
    name       VARCHAR(120) NOT NULL,
    date       DATE NOT NULL,
    created_at DATETIME NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE INDEX ix_workouts_user_id ON workouts (user_id);
CREATE INDEX ix_workouts_id ON workouts (id);

CREATE TABLE workout_exercises (
    id          INTEGER NOT NULL,
    workout_id  INTEGER NOT NULL,
    exercise_id INTEGER NOT NULL,
    order_index INTEGER NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (workout_id)  REFERENCES workouts (id)  ON DELETE CASCADE,
    FOREIGN KEY (exercise_id) REFERENCES exercises (id) ON DELETE RESTRICT
);
CREATE INDEX ix_workout_exercises_workout_id  ON workout_exercises (workout_id);
CREATE INDEX ix_workout_exercises_exercise_id ON workout_exercises (exercise_id);
CREATE INDEX ix_workout_exercises_id          ON workout_exercises (id);

CREATE TABLE sets (
    id                  INTEGER NOT NULL,
    workout_exercise_id INTEGER NOT NULL,
    reps                INTEGER NOT NULL,
    weight              FLOAT NOT NULL,
    order_index         INTEGER NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (workout_exercise_id) REFERENCES workout_exercises (id) ON DELETE CASCADE
);
CREATE INDEX ix_sets_workout_exercise_id ON sets (workout_exercise_id);
CREATE INDEX ix_sets_id ON sets (id);
```

## Alembic bookkeeping table (added by Phase 1)

```sql
CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);
```

It currently holds exactly one row: **`da9c526717c0`** (it held `f3f47238398b` between Phases 1
and 2). This is Alembic's own bookkeeping — it is **not** part of the domain model, has no
relationships, and must never be edited by hand.

## Uniqueness rules, stated plainly

| Rule | Enforced by |
|---|---|
| A global's normalized name is unique among globals | `uq_exercises_global_name_normalized` (partial) |
| A global's slug is unique among globals | `uq_exercises_global_slug` (partial) |
| A user's normalized names are unique among *their* exercises | `uq_exercises_personal_name_normalized` (partial) |
| A global name and a personal name may overlap | the two scopes being separate partial indexes |
| Globals have a slug, personal exercises do not | `ck_exercises_slug_scope` |
| No duplicate tracking type per exercise | `uq_exercise_tracking_type` |
| At most one primary metric per exercise | `uq_exercise_tracking_primary` (partial) |
| At least one primary metric per exercise | **service layer only** (not expressible in SQLite) |
| No duplicate synonym on the same exercise+locale | `uq_exercise_synonyms_scope` |
| No two globals share a synonym; no two of a user's exercises share one | **service layer only** |
| A personal synonym may reuse a global synonym's text | deliberate **absence** of `UNIQUE(locale, synonym_normalized)` |

⚠️ Owner-scoped synonym uniqueness is intentionally *not* in the schema: ownership lives on
`exercises.user_id` and a SQLite index cannot span a join, and a global `UNIQUE(locale, synonym)`
would break the locked rule that a personal alias may reuse a global one (§4.5). Denormalizing
`user_id` onto `exercise_synonyms` was considered and rejected — the locked conceptual schema for the
table does not include it, and a duplicated owner column can drift. The resolver's ambiguity result
is the backstop if duplicates ever appear anyway.

Archived exercises still hold their normalized name: the partial indexes do not exclude them, so a
user cannot reuse the name of their own archived exercise. That is deliberate — silently allowing it
would break any future restore.

## Relationships and deletion behavior

| From | To | Cardinality | DB-level | ORM-level |
|---|---|---|---|---|
| `User` | `Workout` | 1 → N | `ON DELETE CASCADE` | `cascade="all, delete-orphan"` |
| `User` | `Exercise` (personal) | 1 → N | `ON DELETE CASCADE` | **no ORM relationship** — see note below |
| `Workout` | `WorkoutExercise` | 1 → N | `ON DELETE CASCADE` | `cascade="all, delete-orphan"`, `order_by=order_index` |
| `WorkoutExercise` | `Exercise` | N → 1 | `ON DELETE RESTRICT` | plain `relationship`, catalog rows are never deleted |
| `WorkoutExercise` | `Set` | 1 → N | `ON DELETE CASCADE` | `cascade="all, delete-orphan"`, `order_by=order_index` |
| `Exercise` | `ExerciseTracking` | 1 → N | `ON DELETE CASCADE` | `cascade="all, delete-orphan"`, `order_by=id` |
| `Exercise` | `ExerciseSynonym` | 1 → N | `ON DELETE CASCADE` | `cascade="all, delete-orphan"`, `order_by=id` |

`User → Exercise` has **no `User.exercises` ORM relationship**: nothing consumes it, and there is no
user-deletion path in the application. Combined with the PRAGMA below, that means deleting a user by
raw SQL would orphan their personal exercises. Add the relationship (mirroring `User.workouts`) if a
delete-account feature ever lands.

When replacing `Exercise.tracking` or `Exercise.synonyms`, the service clears the collection and
**flushes before** assigning the new rows. SQLAlchemy's default save-before-delete flush order would
otherwise INSERT the new rows before DELETEing the old ones and trip the unique indexes.

⚠️ **SQLite caveat — verified, and STILL UNRESOLVED after Phases 1 and 2.**
**Foreign key enforcement is currently OFF at runtime** (`PRAGMA foreign_keys` reads `0`). SQLite
only enforces foreign keys when `PRAGMA foreign_keys=ON` is set per-connection, and
**`app/core/database.py` does not set it** (there is no `connect` event listener; the only
`connect_args` tweak is `check_same_thread=False`). Phase 1 deliberately did **not** change this.
Consequences:

- The `ON DELETE CASCADE` / `ON DELETE RESTRICT` clauses are recorded in the schema but are
  **currently inert at the engine level**.
- Referential integrity and cascading deletes are enforced **only by the SQLAlchemy ORM cascades**,
  which is why deletes work correctly through the API but would not be protected against raw SQL.
- `ON DELETE RESTRICT` on `workout_exercises.exercise_id` therefore does **not** currently prevent
  deleting a referenced catalog exercise via raw SQL.

It was confirmed during Phase 1 that enabling the PRAGMA is **not** required for safe Alembic
operation: stamping writes only the `alembic_version` row, and the baseline carries the same
CASCADE/RESTRICT clauses either way. Phase 2 confirmed the same for a real batch rebuild — with
foreign keys off, `DROP TABLE exercises` mid-rebuild is permitted and the rename restores
`workout_exercises`' reference; `pragma foreign_key_check` on the live database returns **no
violations**, before and after both phases. Enabling it remains a **behavior change, not
infrastructure** — decide it explicitly, and be aware of it when writing data migrations. Tracked as
debt in §5.

---

# 4. DOMAIN DECISIONS — LOCKED

> These are finalized. Implement them as written. Do not redesign, re-debate, or "improve" them
> without an explicit new instruction from the project owner. None of this is implemented yet
> (except where §2 says otherwise).

## 4.1 Template vs. Session

- **Template and Workout Session are separate entities.**
- Templates contain **intent/targets only**, never actual performance.
- Sessions contain **actual performance**.
- A Session is an **independent snapshot** once created from a template.
- **Editing a Session never modifies its template.**
- **Global templates are immutable.**
- Users can own **personal templates**.
- **Starting a template creates a Session directly** (no intermediate draft step).
- **Personalizing a global template creates a "My Template"** (a personal copy).

## 4.2 "Save Session as My Template" derivation rules

Deriving a template from a performed Session:

- Only exercises with **at least one actually recorded Set** are included.
- Only **actually recorded** Sets count toward generated targets.
- `target_sets` = number of performed Sets.
- reps targets = **MIN/MAX of actually recorded reps**.
- duration targets = **MIN/MAX of recorded duration**.
- distance targets = **MIN/MAX of recorded distance**.
- **The template stores no target weight.**
- The template name is **prefilled** when saving but **editable**.
- **Duplicate personal template names must be rejected** with an error — never auto-suffixed
  ("… (2)" is forbidden).

## 4.3 Tracking model

- `TrackingType` = `reps` | `duration` | `distance`.
- **Weight is NOT a tracking type.** It is an optional attribute of a Set.
- An Exercise has **exactly one primary tracking metric** and **zero or more secondary metrics**.
- A Set **must contain the primary metric**.
- Secondary metrics are optional.
- **Exercise tracking is relational, not JSON.**

## 4.4 Set model

- `weight_kg` **nullable**.
- `weight_kg = 0` is **valid and semantically distinct from NULL** (bodyweight/unloaded vs. unknown).
- Weight precision: **DECIMAL(6,2)**.
- `duration_seconds` INTEGER nullable.
- `distance_meters` INTEGER nullable.
- `RPE` nullable, range **0–10 in 0.5 increments**.
- `RIR` nullable INTEGER **0–5**, where **5 means "5+"**.
- **RPE and RIR are independent** (no derivation of one from the other).
- `set_type` = `warmup` | `working` | `dropset`, default **`working`**.
- **RPE/RIR remain backend-only for now** (no UI).

## 4.5 Exercises

- Support **global exercises** and **user-owned personal exercises**.
- Global exercise: `user_id = NULL`.
- Personal exercise belongs to exactly one user.
- **Minimum personal exercise creation = name + tracking.** All other metadata is optional.
- Personal exercise tracking is **editable until the first actual Set is recorded**; after that,
  **tracking becomes immutable**.
- **Archiving** a personal exercise **preserves historical Session references**.
- An archived exercise **disappears from normal lists and pickers**.
- **No archived/restore UI for now.**
- When a personal exercise is archived, **remove it from future personal templates**.
- **Never modify historical Sessions.**
- The same user **cannot have duplicate normalized personal exercise names**.
- Personal **synonyms are optional**.
- Synonym normalization = **trim + lowercase + collapse internal spaces**.
- **Personal aliases override global aliases** during resolution.
- **Resolution priority:**
  1. personal exact name
  2. personal synonym
  3. global exact name
  4. global synonym
- **Global synonym uniqueness must NOT prevent a personal alias from reusing the same text.**
- Global exercises have **stable unique slugs**.
- Personal exercises **do not require slugs** — use their IDs.

## 4.6 Session

- `started_at` is **timezone-aware**.
- `ended_at` **nullable**.
- `ended_at IS NULL` → **active**.
- `ended_at IS NOT NULL` → **completed**.
- **No explicit Session status enum yet** (derive state from `ended_at`).
- Completed Sessions **remain editable** for corrections.
- **Editing a completed Session does not change `ended_at`.**
- **Do not implement audit/version history yet.**

## 4.7 API design

- Move toward **granular resources**.
- **Sets must have stable IDs.**
- **Do NOT update workouts by deleting and recreating all child Sets.**
- Required conceptual operations:
  - `POST /workout-exercises/{id}/sets`
  - `PATCH /sets/{set_id}`
  - `DELETE /sets/{set_id}`
- The **same principle applies** to adding/removing Session exercises.
- `order_index` remains **compact**: after insertion/deletion, **normalize to `0..N`**.
- **Reordering must never change entity IDs.**

## 4.8 Storage strategy

- **Prefer relational tables** for queryable domain relationships and taxonomies.
- **JSON only** for future optional/non-essential metadata.
- **Do not introduce unnecessary taxonomy tables yet.**

## 4.9 Canonical units

- canonical weight = **kg**
- canonical duration = **seconds**
- canonical distance = **meters**

All storage uses canonical units. Any unit conversion is a presentation concern.

---

# 5. IMPORTANT CURRENT TECHNICAL DEBT

> ✅ **Resolved by Phase 1** and removed from this list: *"No Alembic"* and
> *"`Base.metadata.create_all()` is used at runtime"*. Alembic 1.13.3 now owns schema evolution,
> baseline `f3f47238398b`, and `create_all()` is gone from the startup path and the seeder (§2.9).
>
> ✅ **Resolved by Phase 2** and removed from this list: *"the exercise catalog is read-only with no
> ownership model"*. Phase 2 resolved **none** of the items below — it deliberately touched no Set
> column and no runtime PRAGMA — but it did add items 15–19.

1. **SQLite holds existing real data** (`backend/gym.db`, 9 users / 8 workouts / 58 sets). Migrations
   must be non-destructive. See §6.
2. **The current `Set` requires `reps` and `weight` (both NOT NULL) and cannot represent all
   tracking types.** Duration-based and distance-based exercises are impossible to record today, and
   unloaded exercises cannot distinguish "0 kg" from "no weight concept".
3. **`weight` is `FLOAT`**, not `DECIMAL(6,2)` as decided in §4.4. Migrating requires a value-safe
   conversion.
4. **The frontend calls `/sets` endpoints that the backend does not implement.**
   `frontend/src/api/sets.js` (+ `api_contract.md`) describe `POST /sets`, `PUT /sets/{id}`,
   `DELETE /sets/{id}`. None exist. Currently harmless because the module is unused, but it is a trap.
5. **The current workout update rebuilds `WorkoutExercise` and `Set` rows and changes their IDs.**
   `update_workout` reassigns `workout.exercises`, relying on `delete-orphan`. Live evidence of the
   churn: `sets` has 58 rows but `max(id) = 98`; `workout_exercises` has 17 rows but `max(id) = 32`.
   This **violates the locked decision in §4.7** and must be replaced by granular operations.
6. **Workout date handling is inconsistent and can be wrong around local midnight.**
   `Workout.date` has model default `lambda: datetime.utcnow().date()` (UTC) while
   `service.create_workout` uses `date.today()` (server-local). The service value always wins for
   API-created workouts, so the model default is effectively dead code — but the two disagree, and
   the UTC path is reachable by any client that omits `date`. The frontend currently always sends an
   explicitly computed **local** `YYYY-MM-DD` (`utils/format.js::toDateInputValue`), which masks the
   bug. Decide one timezone policy during the domain phases.
7. **The `Template` entity does not exist at all** — no model, no table, no schema, no endpoint.
8. ⚠️ **The existing `TODO` comments that suggest implementing "Workout-as-template" MUST NOT be
    followed.** Specifically:
    - `app/workouts/routes.py` (~line 33): suggests `POST /workouts/templates` persisting "a
      Workout-like record flagged as a template" plus `POST /workouts/from-template/{id}`.
    - `app/workouts/schemas.py` (bottom): suggests `WorkoutTemplate` schemas cloning a Workout.

    These predate the locked decisions. §4.1 requires Template and Session to be **separate
    entities**, not a boolean flag on `Workout`. Treat these TODOs as obsolete.
9. **No tests and no CI** — every regression is currently caught by hand. Phase 1 deliberately did
   not start a test suite; its verification scripts were kept outside the repository.
10. **Deprecated `datetime.utcnow()`** for `created_at` defaults across models (Python 3.12+ warns).
11. **Dead frontend code**: `api/sets.js`, `components/workouts/RestTimer.jsx`,
    `hooks/useRestTimer.js`, `components/ui/Button.jsx`, `components/ui/Input.jsx`. The last three
    also reference CSS classes that no longer exist.
12. ⚠️ **SQLite foreign keys are NOT enforced — UNRESOLVED, carried forward from Phase 1.**
    **Foreign key enforcement is currently OFF at runtime**: `PRAGMA foreign_keys` reads `0` because
    `PRAGMA foreign_keys=ON` is never issued in `app/core/database.py`. All the
    `ON DELETE CASCADE`/`RESTRICT` clauses are therefore **inert at the engine level**, and
    referential integrity depends **entirely on the SQLAlchemy ORM cascades** (details in §3).
    Deletes work correctly through the API but nothing protects the data against raw SQL.
    Phase 1 confirmed this is **not** required for safe Alembic operation and explicitly left it
    alone, because enabling it is a **behavior change, not infrastructure**. Decide it during the
    domain phases.
13. ⚠️ **The baseline migration's `downgrade()` is destructive.** `downgrade()` on `f3f47238398b`
    drops every table — against the real populated `backend/gym.db` that is total, unrecoverable
    data loss. It exists only so the revision is reversible on throwaway databases.
    **Never run it against the real `gym.db`.**
14. **Stale documentation**: `PRD.md`, `architecture.md`, `api_contract.md`,
    `docs/project-status.md` all disagree with reality and/or with §4 (details in §2.8).
    `api_contract.md` is now additionally stale in the other direction — it does not document the
    three exercise write endpoints Phase 2 added (§2.6). `docs/decision-log.md` is empty.
    `README.md` **was** updated in Phase 1 (Alembic setup and commands) and is accurate on that
    point.
15. **`ExerciseOut.primary_tracking_type` is a required field**, so an exercise row with no primary
    tracking row would make `GET /api/exercises` return **500** rather than degrade. Nothing can
    produce that state today (the migration backfilled all 23, the service always writes tracking in
    the same transaction, and the seeder heals a global that is missing it), and the strictness is
    intentional — it encodes "exactly one primary metric". Be aware of it if you ever insert
    exercises by raw SQL.
16. **Two invariants live only in the service layer**, not in the schema: "at least one primary
    tracking metric per exercise", and owner-scoped synonym uniqueness (§3). A raw-SQL writer can
    violate both. The resolver reports ambiguity rather than crashing if the second one is violated.
17. **No `User.exercises` ORM relationship**, so deleting a user by raw SQL orphans their personal
    exercises while `PRAGMA foreign_keys` is off (§3). Harmless today — there is no delete-account
    path — but it must be added alongside one.
18. **The seeded global synonym list is a curated starting point, not a complete alias set.**
    26 aliases across 18 of the 23 exercises (`app/seed/exercises_seed.py`); `calf-raise`,
    `face-pull`, `front-squat`, `hanging-leg-raise` and `leg-press` have none. Aliases that name a
    *different* movement were deliberately excluded ("Chin Up" for a pull-up, "Hanging Knee Raise"
    for a hanging leg raise, "Bicep Curl" for either curl variant). Expect to curate this.
19. **`exercise_synonyms.locale` is stored but not used.** Everything is seeded as `en` and the
    resolver matches across all locales. It exists so adding real i18n later is not a migration.

## 5.1 Fixed during Phase 1 — pre-existing `seed_db` bug

`backend/scripts/seed_db.py` was **already broken on any fresh database before Phase 1**, and this
was fixed as part of the phase.

- **Cause:** the script imported only `app.auth.models` and `app.exercises.models`. The
  **`app.workouts.models` import was missing**, so when SQLAlchemy configured its mapper registry,
  `User.workouts = relationship("Workout")` could not resolve the name.
- **Symptom:** **mapper configuration failed on a fresh DB** — the first query raised
  `InvalidRequestError: When initializing mapper Mapper[User(users)], expression 'Workout' failed to
  locate a name ('Workout')`.
- **Why it was invisible:** the old `Base.metadata.create_all()` call did **not** mask it —
  `create_all` operates on `MetaData` and never configures mappers. It simply went unnoticed because
  the existing `gym.db` was already seeded, so nobody re-ran the seeder against an empty database.
- **Confirmed pre-existing**, not a Phase 1 regression: replaying the original file's exact logic
  (including its `create_all` call) against a clean database fails identically on the pre-Phase-1
  version of the file.
- **Fix:** added the missing `from app.workouts import models` import. One line.
  **No domain behavior changed** — at that point the seeder was still the same idempotent
  upsert-by-*name* over the same 23 exercises. (Phase 2 later re-keyed it to `slug` — §2.10.)
  Leaving it broken would have been indistinguishable from a Phase 1 regression.

## 5.2 Deliberately deferred by Phase 2 — integration points to honour

These are **not** oversights. Each is a locked decision whose prerequisite does not exist yet.

| Deferred behavior | Where it belongs | Why it could not be done now |
|---|---|---|
| **"A Set must contain the Exercise primary metric"** (§4.3) — Set-side metric validation | **Phase 3 — Set & Tracking** | Phase 2 implements the *Exercise* side of tracking only. `Set` still has NOT NULL `reps` + `weight` and no duration/distance columns, so the rule has nothing to validate against. `exercise_tracking` is the table Phase 3 must read. |
| **"Archiving a personal exercise removes it from future personal templates"** (§4.5) | **Phase 4 — Templates** | No `Template` entity exists — no model, no table (§5.7). `service.archive_personal_exercise` currently only flips `is_active`; its docstring names this deferral so it is found when templates land. |
| **Full frontend adaptation** — tracking UI, personal-exercise UI, archived/restore views, `ExercisePicker` redesign | **Phase 6 — Frontend adaptation** | Phase 2 was backend-scoped. The single one-line null-safety guard in `ExercisePicker.jsx` (§2.10) is a compatibility fix, not adaptation. |
| **`PRAGMA foreign_keys=ON` at runtime** | still undecided (§5.12) | A runtime behavior change, not infrastructure. Phase 2 confirmed again that it is not needed for safe migrations and left it alone. |
| **HTTP resolver endpoint** | whenever a consumer needs it (likely Phase 6/7) | `service.resolve_exercise` is fully implemented and tested, but nothing calls it over HTTP yet, and inventing an endpoint shape without a consumer would be speculative. The AI/voice layer (Phase 7) is its obvious first user. |
| **Restore-from-archive** | not scheduled | §4.5 says "no archived/restore UI for now". No API either, so nothing has to be un-built later. The archived row keeps its normalized name precisely so a restore stays possible (§3). |

---

# 6. DATA SAFETY

> **Read this before touching the database.**

- **`backend/gym.db` contains existing real data.** It is git-ignored, so it exists **only on the
  owner's machine** — there is no copy in the repository and **no remote backup**. Losing it is
  permanent.
- **It must never be reset, deleted, or recreated casually.** Do not drop tables, do not truncate,
  do not re-seed destructively. (`create_all()` no longer exists anywhere in the codebase.)
- ✅ **Alembic was introduced using the baseline + stamp approach** (done in Phase 1): the initial
  revision `f3f47238398b` reproduces the schema exactly, and the existing database was **stamped**
  with it rather than upgraded through it, so no DDL ever ran against the populated tables. From
  here on, every schema change is an **incremental revision** on top of that baseline.
- ⚠️ **Never run `alembic downgrade` against `backend/gym.db`.** The baseline's `downgrade()` drops
  every table (§5.13). `da9c526717c0`'s own `downgrade()` is less dangerous — it refuses outright if
  any personal exercise exists, and otherwise drops the Phase 2 columns and tables — but it still
  destroys tracking and synonym data.
- **Preserve all existing rows AND their primary key values.** Existing IDs are referenced by
  foreign keys and are user-visible in URLs (`/workouts/:id`).
- **Create a backup file before any destructive SQLite migration.** SQLite has limited `ALTER TABLE`
  support, so column type/nullability changes typically require the
  *create new table → copy data → drop old → rename* pattern; Alembic's `batch_alter_table` does
  this. Always copy `gym.db` to a timestamped file first, and verify row counts afterwards.

## Recorded row counts (current — measured 2026-09-01, after Phase 2)

| Table | Rows | `max(id)` |
|---|---|---|
| `users` | **9** | 9 |
| `exercises` | **23** | 23 |
| `workouts` | **8** | 9 |
| `workout_exercises` | **17** | 32 |
| `sets` | **58** | 98 |
| `exercise_tracking` | **23** | 23 |
| `exercise_synonyms` | **26** | 26 |

The first five are unchanged from before Phase 1. **Neither Phase 1 nor Phase 2 changed a single
pre-existing row**, verified both times by a row-level comparison against the pre-migration backup:
all 23 exercise ids, all 17 `workout_exercises.exercise_id` references, and the full `users` /
`workouts` / `sets` tables came back identical, as did the four original `exercises` columns.

`exercise_tracking` (23) and `exercise_synonyms` (26) are new: one primary metric per global
exercise, backfilled by the migration, plus the curated global aliases inserted by the seeder.

`alembic_version` holds **`da9c526717c0`**.

Extra facts useful as invariants: workouts per user = `{user 7: 1, user 8: 5, user 9: 2}`;
`sets` with `weight = 0`: **0**; `pragma foreign_key_check` and `pragma integrity_check` both clean.
The gaps between row counts and `max(id)` are expected — they are the fingerprint of the PUT-rebuild
churn described in §5.5, not data loss.

Phase 2 invariants worth re-checking after any exercise migration: all 23 exercises are global
(`user_id IS NULL`) and active; every `name_normalized` equals `normalize_name(name)`; every global
`slug` equals `slugify_name(name)`; no global normalized-name or slug collisions; exactly one primary
tracking row per exercise; `plank` is the only primary that is not `reps`.

**Any migration must leave these counts identical unless the migration's explicit purpose is to
change data.**

## Backups

| Snapshot | Taken |
|---|---|
| `backend/gym.db.backup-20260830-225004` (73,728 bytes) | immediately before Phase 1 |
| `backend/gym.db.backup-20260901-085211` (81,920 bytes) | at the start of the Phase 2 session |
| `backend/gym.db.backup-20260901-091115` (81,920 bytes) | immediately before applying `da9c526717c0` — **this is the Phase 2 rollback point** |

They are git-ignored via the `*.db.backup-*` rule added to `backend/.gitignore` — the pre-existing
`*.db` rule did **not** match it, so without that rule real user data would have been committed.

Phase 2's migration was additionally **rehearsed on a full copy of `gym.db`** and passed the entire
verification suite there *before* being applied to the real file. Do the same for Phase 3: SQLite
batch rebuilds are the riskiest thing in this project.

---

# 7. NEXT IMPLEMENTATION PHASE

## ✅ PHASE 1 — Alembic Foundation: **COMPLETED**

Delivered: Alembic 1.13.3 installed and configured, baseline revision **`f3f47238398b`**,
`backend/gym.db` preserved and **stamped** (not upgraded) at that baseline, `create_all()` removed
from application startup and from the seeder, `alembic current`/`heads` aligned, row counts
unchanged (9 / 23 / 8 / 17 / 58). Full detail in **§2.9**. Do not redo this work.

Deliberately **not** done in Phase 1, still open: `PRAGMA foreign_keys=ON` (§5.12), and any test
suite (§5.9).

## ✅ PHASE 2 — Exercise Domain: **COMPLETED**

Delivered: revision **`da9c526717c0`** on top of the baseline. Global vs. personal ownership,
persisted normalized names, stable global slugs, relational tracking metadata
(`exercise_tracking`), synonyms (`exercise_synonyms`), the four-level name/synonym resolver, the
tracking freeze after first recorded Set, soft archiving, personal create/update/archive endpoints,
ownership- and archive-aware workout validation, and a slug-keyed idempotent seeder. All 23 existing
exercises kept their ids and became global; row counts unchanged (9 / 23 / 8 / 17 / 58). Full detail
in **§2.10**, resulting schema in **§3**. Do not redo this work.

Deliberately **not** done in Phase 2, still open: everything in **§5.2**, plus
`PRAGMA foreign_keys=ON` (§5.12) and a test suite (§5.9).

## The next task is: PHASE 3 — Set & Tracking.

Scope is defined by the **locked decisions in §4.3 and §4.4** — implement them as written; do not
redesign them. Phase 2 built the Exercise side of tracking; Phase 3 builds the Set side and connects
the two.

Requirements:

- **Implement §4.4 (Set model) and the Set half of §4.3.** `weight_kg` nullable
  `DECIMAL(6,2)` (with `0` semantically distinct from NULL), `duration_seconds` and
  `distance_meters` nullable INTEGER, `RPE` (0–10 in 0.5 steps), `RIR` (0–5, 5 meaning "5+"),
  `set_type` = `warmup | working | dropset` default `working`. RPE/RIR stay backend-only.
- **Enforce "a Set must contain the Exercise primary metric"** (§4.3) by reading
  `exercise_tracking` — that is the deferred rule §5.2 hands over. Secondary metrics stay optional.
- Nothing from §4.1/§4.2 (Templates) or §4.7 (granular APIs) — those remain Phases 4–5. Do not
  replace the destructive workout PUT yet (§5.5).
- **Back up `backend/gym.db` first** (timestamped copy, §6) and record the row counts.
- **Write a real Alembic revision on top of `da9c526717c0`.** `reps` becoming nullable and `weight`
  becoming `DECIMAL(6,2)` are both value-safe conversions that need `batch_alter_table` on SQLite,
  and the `FLOAT → DECIMAL` step needs an explicit, verified data conversion — autogenerate will not
  write it. All 58 existing sets have `reps` and a `weight`, none with `weight = 0` (§6).
- **Rehearse on a copy of `gym.db` before touching the real file** (§6). The migration must preserve
  all existing rows and primary key values, including the `sets` id gaps.
- **Verify row counts before and after**, re-run `alembic check`, and re-check
  `pragma foreign_key_check`.
- **Verify the app still boots and behaves**: `/api/health`, login, list workouts, workout detail
  (verification is still manual — §2.7).
- Remember that **foreign keys are not enforced at runtime** (§5.12); do not rely on the database to
  reject bad references in a data migration.

- **STOP after Phase 3.** Do not begin Phase 4 in the same change. Report results and wait.

---

# 8. FUTURE IMPLEMENTATION ORDER

> Use **this** numbering from now on. It supersedes the older frontend-era "Phase 5 Step N"
> numbering in `docs/project-status.md`.

| Phase | Scope | Status |
|---|---|---|
| **Phase 1** | Alembic Foundation — Alembic + baseline `f3f47238398b` of the existing DB (§2.9) | ✅ **COMPLETED** |
| **Phase 2** | Exercise Domain — global vs. personal, slugs, synonyms/aliases, tracking metadata, archiving (per §4.5) — revision `da9c526717c0` (§2.10) | ✅ **COMPLETED** |
| **Phase 3** | Set / tracking domain (Set-side tracking validation, nullable `weight_kg` as DECIMAL(6,2), duration, distance, RPE, RIR, `set_type` — per §4.3/§4.4) | ← **NEXT** (§7) |
| **Phase 4** | Templates (separate entity, global immutable + personal, start-template-creates-Session, save-Session-as-My-Template derivation — per §4.1/§4.2) | not started |
| **Phase 5** | Granular Session/Set APIs (stable IDs, `POST /workout-exercises/{id}/sets`, `PATCH`/`DELETE /sets/{id}`, `order_index` normalization — per §4.7) | not started |
| **Phase 6** | Frontend adaptation to the new domain and APIs | not started |
| **Phase 7** | AI / voice layer (later) | not started |

Each phase should be a self-contained, reviewable change with its own migration(s). Do not run ahead.

---

# 9. DO NOT DO YET

Explicitly out of scope until the corresponding phase is reached:

- **No AI implementation.** No LLM calls, no AI-assisted logging, no suggestion engine (Phase 7).
- **No voice implementation.** No speech-to-text, no voice logging UI (Phase 7).
- **No unnecessary metadata or taxonomy expansion.** Do not add equipment/movement-pattern/difficulty
  lookup tables, tag systems, or muscle-group taxonomies "while we're here" (§4.8).
- **No exercise media implementation yet.** No images, no video, no thumbnails, no file uploads or
  storage layer.
- **No template-as-workout shortcut.** Do not implement a `is_template` boolean on `Workout`, and do
  not follow the obsolete TODOs in `app/workouts/routes.py` / `schemas.py` (§5.8).
- **No DB reset.** Never drop/recreate `backend/gym.db`, and never `alembic downgrade` against it
  (§6, §5.13).
- **No `PRAGMA foreign_keys=ON` as a drive-by change.** It is a runtime behavior change (§5.12);
  it needs an explicit decision, not a "while we're here" fix.
- **No Templates and no granular Set APIs during Phase 3.** Templates are Phase 4 (§4.1/§4.2) and the
  granular `POST /workout-exercises/{id}/sets` / `PATCH`/`DELETE /sets/{id}` surface is Phase 5
  (§4.7). Do not replace the destructive workout PUT yet (§5.5).
- **No broad frontend Exercise UI.** No tracking UI, no personal-exercise or archive/restore screens,
  no `ExercisePicker` redesign — that is Phase 6 (§5.2). Phase 2's one-line null-safety guard was a
  compatibility fix and is not a precedent for further frontend work.
- **No broad refactor unrelated to the active phase.** In particular, during Phase 3 do **not**:
  migrate models to SQLAlchemy 2.0 `Mapped[]` style, introduce TypeScript, restructure folders,
  delete the dead frontend code from §5.11, rewrite the stale docs, or reformat files. Note them,
  leave them.

---

# 10. REPOSITORY-SPECIFIC REFERENCES

## Repository layout (real paths)

```
gym-tracker-app/
├── agents.md                    # agent role boundaries (backend / frontend / refactor).
│                                #   NOTE: lowercase filename, at the repo ROOT (not in docs/).
│                                #   It serves the AGENTS.md convention role.
├── PRD.md                       # original product doc (STALE re: templates — see §2.8)
├── architecture.md              # STALE schema
├── api_contract.md              # STALE (documents nonexistent /sets)
├── README.md                    # setup instructions (UPDATED in Phase 1: Alembic setup + commands)
├── docs/
│   ├── AI_HANDOFF.md            # ← this file (durable context)
│   ├── project-status.md        # STALE phase numbering
│   └── decision-log.md          # EMPTY
├── backend/
│   ├── .venv/                   # Python venv (git-ignored)
│   ├── gym.db                   # SQLite with REAL DATA (git-ignored) ⚠️
│   ├── gym.db.backup-*          # pre-migration snapshots, REAL DATA (git-ignored) ⚠️
│   ├── .env / .env.example      # .env is git-ignored and present locally
│   ├── requirements.txt         # includes alembic==1.13.3
│   ├── alembic.ini              # Alembic config; sqlalchemy.url intentionally BLANK
│   ├── alembic/
│   │   ├── env.py               # URL from app settings; target_metadata = Base.metadata
│   │   └── versions/
│   │       ├── f3f47238398b_baseline_existing_schema.py   # baseline; downgrade() DROPS ALL ⚠️
│   │       └── da9c526717c0_exercise_domain_foundation.py # Phase 2; head
│   ├── start.bat                # Windows launcher (kills orphan :8000, alembic upgrade head, venv)
│   ├── Dockerfile / docker-compose.yml   # CMD runs `alembic upgrade head` before uvicorn
│   ├── scripts/seed_db.py       # `python -m scripts.seed_db` (requires a migrated schema)
│   └── app/
│       ├── main.py              # app factory; router mounting under /api (NO create_all)
│       ├── core/
│       │   ├── config.py        # pydantic-settings; DATABASE_URL, JWT_*, CORS_ORIGINS
│       │   ├── database.py      # engine, SessionLocal, Base, get_db
│       │   ├── dependencies.py  # get_current_user
│       │   ├── exceptions.py    # NotFoundError/ValidationError + global handlers
│       │   ├── response.py      # ok() → {success, data, error}
│       │   └── security.py      # hashing + JWT create/decode
│       ├── auth/                # models(User) schemas service routes
│       ├── exercises/           # models(Exercise, ExerciseTracking, ExerciseSynonym, TrackingType),
│       │                        #   normalization.py, schemas, service (scoping/CRUD/resolver), routes
│       ├── workouts/            # models(Workout, WorkoutExercise, Set) schemas service routes
│       └── seed/                # exercises_seed.py (23 globals w/ slug + tracking + aliases)
│                                #   + seeder.py (idempotent, keyed by slug)
└── frontend/
    ├── package.json / vite.config.js / tailwind.config.js / postcss.config.js / jsconfig.json
    ├── index.html               # contains anti-FOUC theme script
    └── src/
        ├── main.jsx / App.jsx
        ├── api/                 # axiosClient.js (envelope unwrap + 401 event), auth, exercises,
        │                        #   workouts, sets.js (DEAD — endpoints do not exist)
        ├── context/             # AuthContext.jsx, ThemeContext.jsx
        ├── routes/              # AppRoutes.jsx, ProtectedRoute.jsx, PublicRoute.jsx
        ├── components/
        │   ├── layout/          # AppShell, Header, BottomNav
        │   ├── ui/              # AppButton, AppInput, AuthCard, PageContainer, LoadingScreen,
        │   │                    #   StatusView, Modal, Label, ThemeToggle, (Button/Input = DEAD)
        │   ├── auth/            # LoginForm, RegisterForm
        │   └── workouts/        # WorkoutList, WorkoutCard, WorkoutForm, ExerciseFieldCard,
        │                        #   SetRow, ExercisePicker, RestTimer (UNWIRED)
        ├── pages/               # Home, Login, Register, WorkoutEditor, WorkoutDetail, NotFound
        ├── hooks/               # useAuth, useTheme, useAsync, useRestTimer
        ├── lib/                 # utils.js (cn), validators.js (Zod schemas)
        ├── utils/               # format.js (formatDate, formatWeight, toDateInputValue), storage.js
        └── styles/global.css    # Tailwind + shadcn-style CSS variables
```

## Files to read first, by task

| Task | Start here |
|---|---|
| Migrations (any phase) | `backend/alembic/env.py`, `backend/alembic.ini`, `backend/alembic/versions/`, `backend/app/core/database.py`, `backend/app/core/config.py` |
| Exercise domain (done — Phase 2) | `backend/app/exercises/*` (incl. `normalization.py`), `backend/app/seed/*`, §2.10, §4.5 |
| Phase 3 — Set / tracking (**next**) | `backend/app/workouts/models.py`, `backend/app/workouts/schemas.py`, `backend/app/exercises/models.py` (`ExerciseTracking`, `TrackingType`), §4.3/§4.4 |
| Granular Set APIs | `backend/app/workouts/service.py` (see `update_workout`), `backend/app/workouts/routes.py` |
| Response/error conventions | `backend/app/core/response.py`, `backend/app/core/exceptions.py` |
| Frontend API layer | `frontend/src/api/axiosClient.js` |
| Frontend validation | `frontend/src/lib/validators.js` |
| Workout UI | `frontend/src/components/workouts/WorkoutForm.jsx`, `frontend/src/pages/WorkoutEditorPage.jsx` |

## Commands (Windows / PowerShell — this is a Windows dev machine)

### Backend

```powershell
# from backend/
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# apply migrations (REQUIRED before first run and after pulling a new revision;
# the app no longer creates tables itself). No-op when already at head.
.\.venv\Scripts\python.exe -m alembic upgrade head

# run the API (preferred: kills orphan :8000, then runs `alembic upgrade head`, then serves)
.\start.bat

# or manually (does NOT migrate — run alembic upgrade head yourself first)
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# seed the exercise catalog (idempotent; requires an already-migrated schema)
.\.venv\Scripts\python.exe -m scripts.seed_db
```

### Alembic

```powershell
# from backend/ — ALWAYS from backend/, the default SQLite URL is relative
.\.venv\Scripts\python.exe -m alembic current    # revision the local DB is on
.\.venv\Scripts\python.exe -m alembic heads      # latest revision available
.\.venv\Scripts\python.exe -m alembic history    # revision graph
.\.venv\Scripts\python.exe -m alembic check      # fails if models drifted from migrations
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m alembic revision --autogenerate -m "describe the change"

# run a migration against a throwaway DB instead of gym.db (verification only)
.\.venv\Scripts\python.exe -m alembic -x db_url=sqlite:///C:/temp/scratch.db upgrade head
```

- Current state: `alembic current` and `alembic heads` both report **`da9c526717c0 (head)`**, and
  `alembic check` is clean. The graph is linear: `f3f47238398b → da9c526717c0`.
- Alembic reads `DATABASE_URL` through `app/core/config.py` — the same source the app uses.
  `sqlalchemy.url` in `alembic.ini` is blank **on purpose**; do not fill it in.
- ⚠️ **Never run `alembic downgrade` against `gym.db`** — the baseline's `downgrade()` drops every
  table (§5.13). Use the `-x db_url=...` override to test downgrades on a scratch database.
- **Always review autogenerated revisions by hand.** Autogenerate does not infer data backfills, and
  it sorts constraints alphabetically (which is why the baseline's two `workout_exercises` foreign
  keys were manually reordered to match the pre-existing DDL). Phase 2's revision was written
  **entirely by hand** (`alembic revision` without `--autogenerate`) because it needs partial
  indexes, ordered batch rebuilds and explicit backfills; `alembic check` was then used to prove the
  models and the migration agree.
- **Rehearse any data-touching revision on a copy of `gym.db` first** — see §6.

- Swagger UI: `http://localhost:8000/docs` · Health: `http://localhost:8000/api/health`
- **Always use `.venv\Scripts\python.exe`**, not a global `python`/`uvicorn`.
- Known Windows pitfall: `[WinError 10013]` on startup means an orphan process still holds port
  8000 — `start.bat` already kills it.

### Backup the database before migrations

```powershell
# from backend/
Copy-Item gym.db "gym.db.backup-$(Get-Date -Format yyyyMMdd-HHmmss)"
```

These snapshots are git-ignored via `*.db.backup-*` in `backend/.gitignore`. Existing snapshots are
listed in §6; the Phase 2 rollback point is `gym.db.backup-20260901-091115`.

### Inspect the database

```powershell
# from backend/ - schema + row counts
.\.venv\Scripts\python.exe -c "import sqlite3;c=sqlite3.connect('gym.db');print([r[0] for r in c.execute(\"select sql from sqlite_master where type='table'\")]);print([(t,c.execute('select count(*) from '+t).fetchone()[0]) for t in ['users','exercises','workouts','workout_exercises','sets']])"

# current alembic revision recorded in the DB itself
.\.venv\Scripts\python.exe -c "import sqlite3;print(sqlite3.connect('gym.db').execute('select version_num from alembic_version').fetchall())"
```

> PowerShell quoting note: for anything longer, pipe a here-string into
> `.\.venv\Scripts\python.exe -` instead of using `-c`, to avoid quoting errors.

### Frontend

```powershell
# from frontend/
npm install
npm run dev     # http://localhost:5173, host: true (exposed on the LAN for phone testing)
npm run build
```

- Node.js LTS is installed system-wide via winget (`OpenJS.NodeJS.LTS`). If `npm` is "not
  recognized", the PATH has not been refreshed — open a new terminal.
- **Dev API access:** there is **no `frontend/.env`**, so `VITE_API_BASE_URL` is undefined and
  Axios falls back to `baseURL = '/api'`, which is served by the Vite dev proxy
  (`/api` → `http://localhost:8000`). This is why LAN/phone testing works without adding the phone's
  IP to `CORS_ORIGINS` — requests are same-origin from the browser's point of view. If you set
  `VITE_API_BASE_URL` to an absolute URL, you bypass the proxy and **will** need to extend
  `CORS_ORIGINS` in `backend/.env` (currently `http://localhost:5173` only).

### Getting a bearer token for manual API testing

```powershell
$body = '{"email":"you@example.com","password":"your-password"}'
$r = Invoke-RestMethod -Uri http://localhost:8000/api/auth/login -Method Post -Body $body -ContentType 'application/json'
$token = $r.data.access_token
Invoke-RestMethod -Uri http://localhost:8000/api/workouts -Headers @{ Authorization = "Bearer $token" }
```

## Conventions to preserve

- Modular monolith: one folder per domain, each with `models / schemas / service / routes`.
- `service.py` never imports FastAPI; `routes.py` stays thin.
- Every response goes through the `{success, data, error}` envelope (`core/response.py`).
- Domain errors are raised as `NotFoundError` / `ValidationError` and translated by the global
  handlers in `core/exceptions.py`.
- Cross-user access returns "not found", never "forbidden". Validation errors that could otherwise
  reveal another user's data must be indistinguishable from "unknown id" (see
  `_validate_exercise_ids`, §2.3).
- **Name/alias comparisons always go through `app/exercises/normalization.py`**, and the normalized
  value is persisted rather than computed at query time. Migrations inline a frozen copy of those
  helpers instead of importing them, so a revision keeps producing the values it produced when it
  was written.
- Backend models currently use the **legacy `Column(...)` style** — stay consistent within a phase
  rather than mixing styles.
- **Every schema change ships as an Alembic revision.** Never reintroduce `create_all()`, and never
  hand-edit the database to match a model.
- Frontend is **JavaScript/JSX only**; use the `@/` path alias; keep components mobile-first.
- Per `agents.md` (repo root), backend and frontend changes are separate concerns — avoid touching
  both in one phase unless the phase explicitly requires it (Phase 6).

## Maintaining this document

When a phase completes, update: the project-state banner at the top (phase status and next task),
§2 (implementation state), §3 (schema), §5 (resolved debt — move items out of the list rather than
leaving them "done"), §6 (row counts if they changed), §7 (next phase), and §8 (progress). Record
new architectural decisions in §4 **and** in `docs/decision-log.md`. Keep the implemented/planned
distinction rigorous — it is the main value of this file.

**Do not record commit hashes here.** Git already tracks them, and a hash written into this file is
stale the moment anything is committed. Describe state semantically — by phase, by baseline revision
id, by what was verified — so this document only changes when the *project state* changes, not when
the repository does.

**Last verified:** 2026-09-01, after Phase 2 (Exercise Domain) completed. Locked decisions in §4 were
**not** touched by that update and remain exactly as originally agreed — §4.5 in particular is now
*implemented* (§2.2, §2.10) rather than merely decided, apart from the template-cleanup rule
deliberately deferred to Phase 4 (§5.2).
