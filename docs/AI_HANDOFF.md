# AI HANDOFF — Gym Tracker

> **Purpose of this file.** This is the permanent, self-contained context document for any AI coding
> agent joining this project with **zero** access to previous conversations. It records what is
> *actually implemented today*, the *locked* domain decisions that must not be re-litigated, the known
> technical debt, and the exact next task.
>
> **Snapshot date:** 2026-08-30 · **Branch:** `main` · **HEAD:** `1176121` ("review the workout days nomination's")
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
| Migrations | **NONE** — `Base.metadata.create_all()` at startup (see §5) |
| Tests | **NONE** (no test files, no pytest in `requirements.txt`) |

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
backend/app/
  main.py            # app factory: CORS, model imports, create_all, router mounting
  core/              # config, database, dependencies, exceptions, response envelope, security
  auth/              # User model, register/login/me
  exercises/         # Exercise catalog (read-only API)
  workouts/          # Workout + WorkoutExercise + Set
  seed/              # predefined exercise catalog + idempotent seeder
  scripts/seed_db.py # CLI seeding entrypoint
```

Hard rules already followed by the codebase:

- `service.py` contains business logic and **never imports FastAPI primitives**.
- `routes.py` is thin: dependency injection + call service + wrap in response envelope.
- Every API response is wrapped as `{ "success": bool, "data": any, "error": str|null }` via
  `app/core/response.py` and the global exception handlers in `app/core/exceptions.py`.
- All routers are mounted under `/api`.

---

# 2. CURRENT IMPLEMENTATION STATE

> Everything in this section is verified against the repository at HEAD `1176121`.
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

## 2.2 Exercises — MINIMAL, READ-ONLY

- Single endpoint: `GET /api/exercises` (auth required), returns the whole catalog ordered by
  `muscle_group, name`. No pagination, no search, no filters.
- `Exercise` has exactly four fields: `id`, `name`, `muscle_group`, `created_at`.
- Catalog is populated by an idempotent seeder (`app/seed/seeder.py`) from a hardcoded list of
  **23 exercises** (`app/seed/exercises_seed.py`). The seeder upserts **by `name`** and only
  *inserts missing* rows — it does not update metadata of existing rows.
- Current DB catalog: 23 rows across 6 muscle groups (Legs 6, Arms 4, Back 4, Chest 3, Core 3,
  Shoulders 3).

**NOT implemented:** global vs. personal exercises, `user_id` on exercises, slugs, synonyms/aliases,
equipment, movement pattern, exercise type, difficulty, multiple muscle groups, tracking metadata,
archiving, media/images, any write endpoint (create/update/delete).

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
- `_validate_exercise_ids` batch-validates all referenced `exercise_id`s in one query and raises
  `ValidationError` listing unknown ids.
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
| `/login` | `LoginPage` | public-only; authenticated users are redirected away |
| `/register` | `RegisterPage` | public-only |
| `/` | `HomePage` | protected |
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
(Swagger UI, browser, ad-hoc scripts).

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
   implemented (`StatusView`), and the real next task is now **Phase 1 — Alembic** (§7).
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

---

# 3. CURRENT DATABASE SCHEMA

This is the **exact live schema** of `backend/gym.db` as generated by
`Base.metadata.create_all()`, dumped from `sqlite_master` on 2026-08-30 — i.e. the state that the
Alembic baseline in Phase 1 must reproduce faithfully.

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

CREATE TABLE exercises (
    id           INTEGER NOT NULL,
    name         VARCHAR(120) NOT NULL,
    muscle_group VARCHAR(60) NOT NULL,
    created_at   DATETIME NOT NULL,
    PRIMARY KEY (id)
);
CREATE UNIQUE INDEX ix_exercises_name ON exercises (name);
CREATE INDEX ix_exercises_muscle_group ON exercises (muscle_group);
CREATE INDEX ix_exercises_id ON exercises (id);

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

There is **no `alembic_version` table** yet (verified).

## Relationships and deletion behavior

| From | To | Cardinality | DB-level | ORM-level |
|---|---|---|---|---|
| `User` | `Workout` | 1 → N | `ON DELETE CASCADE` | `cascade="all, delete-orphan"` |
| `Workout` | `WorkoutExercise` | 1 → N | `ON DELETE CASCADE` | `cascade="all, delete-orphan"`, `order_by=order_index` |
| `WorkoutExercise` | `Exercise` | N → 1 | `ON DELETE RESTRICT` | plain `relationship`, catalog rows are never deleted |
| `WorkoutExercise` | `Set` | 1 → N | `ON DELETE CASCADE` | `cascade="all, delete-orphan"`, `order_by=order_index` |

⚠️ **SQLite caveat — verified.** SQLite only enforces foreign keys when `PRAGMA foreign_keys=ON` is
set per-connection, and **`app/core/database.py` does not set it** (there is no `connect` event
listener; the only `connect_args` tweak is `check_same_thread=False`). Consequences:

- The `ON DELETE CASCADE` / `ON DELETE RESTRICT` clauses are recorded in the schema but are
  **currently inert at the engine level**.
- Referential integrity and cascading deletes are enforced **only by the SQLAlchemy ORM cascades**,
  which is why deletes work correctly through the API but would not be protected against raw SQL.
- `ON DELETE RESTRICT` on `workout_exercises.exercise_id` therefore does **not** currently prevent
  deleting a referenced catalog exercise via raw SQL.

Do not "fix" this during Phase 1 (it is a behavior change, not infrastructure). Note it for the
domain phases, and be aware of it when writing data migrations.

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

1. **No Alembic.** There is no migration tooling, no `alembic.ini`, no `versions/` directory, and no
   `alembic_version` table in the DB. Only `TODO` comments referencing it.
2. **`Base.metadata.create_all()` is used at runtime.** Called in `app/main.py::create_app()` (line
   ~43) on every startup, and again in `backend/scripts/seed_db.py`. This creates missing tables but
   **can never alter existing ones**, so no schema evolution is currently possible.
3. **SQLite holds existing real data** (`backend/gym.db`, 9 users / 8 workouts / 58 sets). Migrations
   must be non-destructive. See §6.
4. **The current `Set` requires `reps` and `weight` (both NOT NULL) and cannot represent all
   tracking types.** Duration-based and distance-based exercises are impossible to record today, and
   unloaded exercises cannot distinguish "0 kg" from "no weight concept".
5. **`weight` is `FLOAT`**, not `DECIMAL(6,2)` as decided in §4.4. Migrating requires a value-safe
   conversion.
6. **The frontend calls `/sets` endpoints that the backend does not implement.**
   `frontend/src/api/sets.js` (+ `api_contract.md`) describe `POST /sets`, `PUT /sets/{id}`,
   `DELETE /sets/{id}`. None exist. Currently harmless because the module is unused, but it is a trap.
7. **The current workout update rebuilds `WorkoutExercise` and `Set` rows and changes their IDs.**
   `update_workout` reassigns `workout.exercises`, relying on `delete-orphan`. Live evidence of the
   churn: `sets` has 58 rows but `max(id) = 98`; `workout_exercises` has 17 rows but `max(id) = 32`.
   This **violates the locked decision in §4.7** and must be replaced by granular operations.
8. **Workout date handling is inconsistent and can be wrong around local midnight.**
   `Workout.date` has model default `lambda: datetime.utcnow().date()` (UTC) while
   `service.create_workout` uses `date.today()` (server-local). The service value always wins for
   API-created workouts, so the model default is effectively dead code — but the two disagree, and
   the UTC path is reachable by any client that omits `date`. The frontend currently always sends an
   explicitly computed **local** `YYYY-MM-DD` (`utils/format.js::toDateInputValue`), which masks the
   bug. Decide one timezone policy during the domain phases.
9. **The `Template` entity does not exist at all** — no model, no table, no schema, no endpoint.
10. ⚠️ **The existing `TODO` comments that suggest implementing "Workout-as-template" MUST NOT be
    followed.** Specifically:
    - `app/workouts/routes.py` (~line 33): suggests `POST /workouts/templates` persisting "a
      Workout-like record flagged as a template" plus `POST /workouts/from-template/{id}`.
    - `app/workouts/schemas.py` (bottom): suggests `WorkoutTemplate` schemas cloning a Workout.

    These predate the locked decisions. §4.1 requires Template and Session to be **separate
    entities**, not a boolean flag on `Workout`. Treat these TODOs as obsolete.
11. **No tests and no CI** — every regression is currently caught by hand.
12. **Deprecated `datetime.utcnow()`** for `created_at` defaults across models (Python 3.12+ warns).
13. **Dead frontend code**: `api/sets.js`, `components/workouts/RestTimer.jsx`,
    `hooks/useRestTimer.js`, `components/ui/Button.jsx`, `components/ui/Input.jsx`. The last three
    also reference CSS classes that no longer exist.
14. **SQLite foreign keys are not enforced.** `PRAGMA foreign_keys=ON` is never issued, so all the
    `ON DELETE CASCADE`/`RESTRICT` clauses are inert at the engine level and integrity depends
    entirely on the ORM (details in §3).
15. **Stale documentation**: `PRD.md`, `architecture.md`, `api_contract.md`,
    `docs/project-status.md` all disagree with reality and/or with §4 (details in §2.8).
    `docs/decision-log.md` is empty.

---

# 6. DATA SAFETY

> **Read this before touching the database.**

- **`backend/gym.db` contains existing real data.** It is git-ignored, so it exists **only on the
  owner's machine** — there is no copy in the repository and **no remote backup**. Losing it is
  permanent.
- **It must never be reset, deleted, or recreated casually.** Do not "just re-run create_all on a
  fresh DB", do not drop tables, do not truncate, do not re-seed destructively.
- **Alembic must be introduced using a baseline + incremental migrations** approach: generate an
  initial revision that reproduces the *current* schema exactly, then `stamp` the existing database
  with it so Alembic considers it already applied. Never let the first migration try to create
  tables that already hold data.
- **Preserve all existing rows AND their primary key values.** Existing IDs are referenced by
  foreign keys and are user-visible in URLs (`/workouts/:id`).
- **Create a backup file before any destructive SQLite migration.** SQLite has limited `ALTER TABLE`
  support, so column type/nullability changes typically require the
  *create new table → copy data → drop old → rename* pattern; Alembic's `batch_alter_table` does
  this. Always copy `gym.db` to a timestamped file first, and verify row counts afterwards.

## Recorded row counts (measured 2026-08-30, before any migration)

| Table | Rows | `max(id)` |
|---|---|---|
| `users` | **9** | 9 |
| `exercises` | **23** | 23 |
| `workouts` | **8** | 9 |
| `workout_exercises` | **17** | 32 |
| `sets` | **58** | 98 |

File size: **73,728 bytes**. `alembic_version` table: **absent**.

Extra facts useful as invariants: workouts per user = `{user 7: 1, user 8: 5, user 9: 2}`;
`sets` with `weight = 0`: **0**. The gaps between row counts and `max(id)` are expected — they are
the fingerprint of the PUT-rebuild churn described in §5.7, not data loss.

**Any migration must leave these counts identical unless the migration's explicit purpose is to
change data.**

---

# 7. NEXT IMPLEMENTATION PHASE

## The next task is: PHASE 1 — Alembic + baseline of the existing SQLite DB.

This phase is **infrastructure only**.

Requirements:

- **Infrastructure-only.** Add and wire up Alembic. Nothing else.
- **No domain schema evolution yet.** Do not add, rename, retype, or drop a single column. No
  Template entity, no tracking columns, no nullable weight — those are Phases 2+.
- **Back up `backend/gym.db` first** (timestamped copy) and record the row counts from §6.
- **Inspect `Base.metadata.create_all()`** usage before changing it: `app/main.py::create_app()`
  and `backend/scripts/seed_db.py`. Understand what it currently produces (§3 is that output).
- **Baseline the current schema**: create the initial Alembic revision so that applying it to an
  empty database yields *exactly* the schema in §3 — same tables, columns, types, nullability,
  indexes (including the unique indexes on `users.email` and `exercises.name`), and foreign keys
  with their `CASCADE` / `RESTRICT` behavior.
- **Stamp the existing DB** with that baseline revision so Alembic records it as already applied,
  without re-running DDL against the populated database.
- **Verify all row counts before and after** the operation, against §6.
- **Verify the FastAPI app still boots and behaves**: `/api/health`, login, list workouts, workout
  detail. (There are no automated tests to run — §2.7 — so this verification is manual. Adding a
  minimal smoke test is acceptable but must not turn into a broad test-suite project.)
- Ensure Alembic reads `DATABASE_URL` from the same settings source as the app
  (`app/core/config.py`) rather than hardcoding a URL, and make sure all model modules are imported
  in `env.py` so autogenerate sees the full metadata.
- Decide and document how `create_all()` is retired (e.g. keep it out of the startup path and rely
  on `alembic upgrade head`), without breaking local dev or the seeder.

- **STOP after Phase 1.** Do not begin Phase 2 in the same change. Report results and wait.

---

# 8. FUTURE IMPLEMENTATION ORDER

> Use **this** numbering from now on. It supersedes the older frontend-era "Phase 5 Step N"
> numbering in `docs/project-status.md`.

| Phase | Scope |
|---|---|
| **Phase 1** | Alembic + baseline of the existing DB (**current next task**, §7) |
| **Phase 2** | Exercise domain foundation (global vs. personal, slugs, synonyms/aliases, tracking metadata, archiving — per §4.5) |
| **Phase 3** | Set / tracking domain (tracking types, nullable `weight_kg` as DECIMAL(6,2), duration, distance, RPE, RIR, `set_type` — per §4.3/§4.4) |
| **Phase 4** | Templates (separate entity, global immutable + personal, start-template-creates-Session, save-Session-as-My-Template derivation — per §4.1/§4.2) |
| **Phase 5** | Granular Session/Set APIs (stable IDs, `POST /workout-exercises/{id}/sets`, `PATCH`/`DELETE /sets/{id}`, `order_index` normalization — per §4.7) |
| **Phase 6** | Frontend adaptation to the new domain and APIs |
| **Phase 7** | AI / voice layer (later) |

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
  not follow the obsolete TODOs in `app/workouts/routes.py` / `schemas.py` (§5.10).
- **No DB reset.** Never drop/recreate `backend/gym.db` (§6).
- **No broad refactor unrelated to the active phase.** In particular, during Phase 1 do **not**:
  migrate models to SQLAlchemy 2.0 `Mapped[]` style, introduce TypeScript, restructure folders,
  delete the dead frontend code from §5.13, rewrite the stale docs, or reformat files. Note them,
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
├── README.md                    # setup instructions
├── docs/
│   ├── AI_HANDOFF.md            # ← this file (durable context)
│   ├── project-status.md        # STALE phase numbering
│   └── decision-log.md          # EMPTY
├── backend/
│   ├── .venv/                   # Python venv (git-ignored)
│   ├── gym.db                   # SQLite with REAL DATA (git-ignored) ⚠️
│   ├── .env / .env.example      # .env is git-ignored and present locally
│   ├── requirements.txt
│   ├── start.bat                # Windows launcher (kills orphan :8000, uses venv)
│   ├── Dockerfile / docker-compose.yml
│   ├── scripts/seed_db.py       # `python -m scripts.seed_db`
│   └── app/
│       ├── main.py              # app factory; create_all(); router mounting under /api
│       ├── core/
│       │   ├── config.py        # pydantic-settings; DATABASE_URL, JWT_*, CORS_ORIGINS
│       │   ├── database.py      # engine, SessionLocal, Base, get_db
│       │   ├── dependencies.py  # get_current_user
│       │   ├── exceptions.py    # NotFoundError/ValidationError + global handlers
│       │   ├── response.py      # ok() → {success, data, error}
│       │   └── security.py      # hashing + JWT create/decode
│       ├── auth/                # models(User) schemas service routes
│       ├── exercises/           # models(Exercise) schemas service routes
│       ├── workouts/            # models(Workout, WorkoutExercise, Set) schemas service routes
│       └── seed/                # exercises_seed.py (23 items) + seeder.py (idempotent by name)
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
| Phase 1 (Alembic) | `backend/app/main.py`, `backend/app/core/database.py`, `backend/app/core/config.py`, `backend/scripts/seed_db.py`, all `*/models.py` |
| Exercise domain | `backend/app/exercises/*`, `backend/app/seed/*` |
| Set / tracking domain | `backend/app/workouts/models.py`, `backend/app/workouts/schemas.py` |
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

# run the API (preferred: handles orphan process on port 8000)
.\start.bat

# or manually
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# seed the exercise catalog (idempotent)
.\.venv\Scripts\python.exe -m scripts.seed_db
```

- Swagger UI: `http://localhost:8000/docs` · Health: `http://localhost:8000/api/health`
- **Always use `.venv\Scripts\python.exe`**, not a global `python`/`uvicorn`.
- Known Windows pitfall: `[WinError 10013]` on startup means an orphan process still holds port
  8000 — `start.bat` already kills it.

### Backup the database before migrations

```powershell
# from backend/
Copy-Item gym.db "gym.db.backup-$(Get-Date -Format yyyyMMdd-HHmmss)"
```

### Inspect the database

```powershell
# from backend/ - schema + row counts
.\.venv\Scripts\python.exe -c "import sqlite3;c=sqlite3.connect('gym.db');print([r[0] for r in c.execute(\"select sql from sqlite_master where type='table'\")]);print([(t,c.execute('select count(*) from '+t).fetchone()[0]) for t in ['users','exercises','workouts','workout_exercises','sets']])"
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
- Cross-user access returns "not found", never "forbidden".
- Backend models currently use the **legacy `Column(...)` style** — stay consistent within a phase
  rather than mixing styles.
- Frontend is **JavaScript/JSX only**; use the `@/` path alias; keep components mobile-first.
- Per `agents.md` (repo root), backend and frontend changes are separate concerns — avoid touching
  both in one phase unless the phase explicitly requires it (Phase 6).

## Maintaining this document

When a phase completes, update: §2 (implementation state), §3 (schema), §5 (resolved debt), §6 (row
counts if they changed), §7 (next phase), and §8 (progress). Record new architectural decisions in
§4 **and** in `docs/decision-log.md`. Keep the implemented/planned distinction rigorous — it is the
main value of this file.
