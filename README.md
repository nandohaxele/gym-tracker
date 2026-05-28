# Gym Tracker

A simple, mobile-first workout tracking web app for personal use. Full-stack scaffold:
a FastAPI modular monolith backend and a Vite + React JavaScript frontend.

> Status: project skeleton only. Files contain module docstrings and `TODO` markers
> describing what each piece will hold once business logic is implemented.

---

## 1. Repository layout

```
gym-tracker-app/
├── backend/                 FastAPI modular monolith (Python 3.12+)
│   ├── app/
│   │   ├── core/            config, db, security, deps, response envelope, exceptions
│   │   ├── auth/            User model, JWT register/login/me
│   │   ├── exercises/       seeded exercise catalog (read-only API)
│   │   ├── workouts/        Workout, WorkoutExercise, Set + CRUD
│   │   ├── seed/            predefined exercises + idempotent seeder
│   │   └── main.py          FastAPI app factory
│   ├── scripts/seed_db.py   CLI: python -m scripts.seed_db
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── .env.example
├── frontend/                React (Vite, JavaScript)
│   ├── src/
│   │   ├── api/             Axios client + per-resource modules
│   │   ├── context/         AuthContext, ThemeContext
│   │   ├── hooks/           useAuth, useTheme, useRestTimer
│   │   ├── routes/          AppRoutes, ProtectedRoute
│   │   ├── pages/           Login, Register, Home, WorkoutEditor, WorkoutDetail, 404
│   │   ├── components/      layout, auth, workouts, ui
│   │   ├── styles/          theme.css (CSS vars), global.css (mobile-first)
│   │   └── utils/           storage.js, format.js
│   ├── index.html
│   ├── vite.config.js
│   ├── package.json
│   └── .env.example
├── PRD.md                   product requirements
├── architecture.md          architecture + DB schema
├── api_contract.md          REST endpoints + envelope
├── agents.md                agent ownership boundaries
└── README.md                this file
```

---

## 2. Architecture decisions

### Backend - modular monolith

- **Pattern**: each domain (auth, exercises, workouts) is a self-contained module
  owning its own `models.py`, `schemas.py`, `service.py`, `routes.py`. Cross-cutting
  concerns live in `core/` (config, database, security, dependencies, response, exceptions).
- **Why**: the PRD scope is small (personal use) and a monolith is the simplest
  thing that works. The strict module boundaries make it trivial to extract any
  module into its own service later if needed.
- **Response envelope**: every endpoint returns `{ success, data, error }` per
  `api_contract.md`. `core/response.py` provides `ok(data)` / `fail(error)` helpers,
  and `core/exceptions.py` registers handlers that wrap thrown exceptions in the
  same envelope - so business code never has to format JSON manually.
- **Database**: SQLAlchemy 2.x with SQLite for local development. The engine
  applies the `check_same_thread=False` SQLite-specific arg conditionally, so
  pointing `DATABASE_URL` at PostgreSQL is the only change needed at the code
  level (see "Migration to PostgreSQL" below).
- **Auth**: JWT bearer tokens via `python-jose`, password hashing via `passlib[bcrypt]`.
  A single `get_current_user` dependency is reused by every protected route.
- **Seed mechanism**: `app/seed/exercises_seed.py` is the single source of truth for
  the predefined exercise catalog. `app/seed/seeder.py:run_seed(db)` is idempotent
  (skips existing rows by name) and is invoked from `scripts/seed_db.py`.
- **Config**: `pydantic-settings` reads `.env`, never hardcodes secrets. Only
  `.env.example` is committed.

### Frontend - React + Vite (JavaScript), mobile-first

- **Why JavaScript**: the V1 PRD is small and personal; TypeScript adds
  scaffolding cost we don't yet need. The folder structure is designed to make
  a future TS migration mechanical.
- **Mobile-first**: target device is the Galaxy S21 (360x800). The CSS uses
  `dvh` units, safe-area insets, and a 480px max-width container. All tap
  targets are at least 44px tall.
- **Dark mode**: a `ThemeContext` flips `data-theme` on `<html>` and persists
  the choice in `localStorage`. All colors come from CSS variables in
  `styles/theme.css`, so adding/refining themes never touches components.
- **HTTP layer**: a single Axios instance in `api/axiosClient.js` attaches the
  JWT bearer, unwraps the `{success,data,error}` envelope, and handles 401
  globally. Per-resource modules (`auth.js`, `workouts.js`, ...) are thin.
- **Routing**: `react-router-dom` v6 nested routes; a `ProtectedRoute` guard
  redirects to `/login` when there is no token.
- **Rest timer**: `useRestTimer` is intentionally frontend-only per PRD.

---

## 3. Setup

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
copy .env.example .env   # then edit JWT_SECRET, etc.
python -m scripts.seed_db
uvicorn app.main:app --reload
```

API will be available at `http://localhost:8000` (docs at `/docs`).

### Frontend

```bash
cd frontend
npm install
copy .env.example .env   # then adjust VITE_API_BASE_URL if needed
npm run dev
```

App will be available at `http://localhost:5173`.
The Vite dev server proxies `/api` to `http://localhost:8000`.

### Docker (backend)

```bash
cd backend
docker compose up --build
```

The compose file currently runs only the `api` service against SQLite. The
`db` (PostgreSQL) service is included as a commented-out block and can be
enabled when you migrate.

---

## 4. API contract (recap)

All responses follow `{ success: boolean, data: any, error: string | null }`.

| Method | Path                | Auth | Notes                            |
| ------ | ------------------- | ---- | -------------------------------- |
| POST   | /api/auth/register  | no   | Create account                   |
| POST   | /api/auth/login     | no   | Returns JWT                      |
| GET    | /api/auth/me        | yes  | Current user                     |
| GET    | /api/exercises      | yes  | Seeded catalog                   |
| GET    | /api/workouts       | yes  | List user's workouts             |
| POST   | /api/workouts       | yes  | Create workout (nested setup ok) |
| GET    | /api/workouts/{id}  | yes  | Single workout                   |
| PUT    | /api/workouts/{id}  | yes  | Update workout                   |
| DELETE | /api/workouts/{id}  | yes  | Delete workout                   |
| POST   | /api/sets           | yes  | Create set                       |
| PUT    | /api/sets/{id}      | yes  | Update set                       |
| DELETE | /api/sets/{id}      | yes  | Delete set                       |

Authentication: `Authorization: Bearer <jwt>`.

---

## 5. Migration to PostgreSQL

When you outgrow SQLite (per `architecture.md` Future Scalability):

1. Uncomment `psycopg2-binary` in [backend/requirements.txt](backend/requirements.txt)
   and reinstall.
2. Set `DATABASE_URL=postgresql+psycopg2://user:pass@host:5432/gym` in `.env`.
3. (Recommended) Add Alembic for migrations:

   ```bash
   pip install alembic
   alembic init backend/alembic
   ```

   Wire `target_metadata = Base.metadata` and switch from
   `Base.metadata.create_all` (used in dev/seed) to versioned migrations.
4. Uncomment the `db` service and `depends_on` block in
   [backend/docker-compose.yml](backend/docker-compose.yml).

The application code itself - models, services, routes - does not change.

---

## 6. Module ownership

Per [agents.md](agents.md):

- **Backend agent** owns everything under `backend/`.
- **Frontend agent** owns everything under `frontend/`.
- **Refactor agent** is allowed to touch both, but only for cleanup,
  type-safety, naming consistency, and de-duplication.

---

## 7. Roadmap (out of scope for V1)

Per `PRD.md`, V1 explicitly does not include:

- AI suggestions
- Social features
- Advanced analytics
- Programs / templates

These can be added later as additional backend modules without touching the
existing ones, which is the main reason the modular monolith pattern was chosen.
