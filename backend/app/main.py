"""FastAPI application entrypoint.

Wires together the modular monolith:
- Loads settings from environment.
- Creates the FastAPI app and configures CORS.
- Includes the routers from each implemented module under /api.
- Registers global exception handlers that wrap responses in {success, data, error}.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import Base, engine
from app.core.exceptions import register_exception_handlers
from app.core.response import ok


def create_app() -> FastAPI:
    """Application factory."""
    settings = get_settings()

    app = FastAPI(
        title="Gym Tracker API",
        version="0.1.0",
        description="Modular monolith backend for the Gym Tracker web app.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Importing the model modules registers them on Base.metadata before create_all.
    from app.auth import models as _auth_models  # noqa: F401
    from app.exercises import models as _exercises_models  # noqa: F401
    from app.workouts import models as _workouts_models  # noqa: F401

    # TODO (future): replace create_all with Alembic migrations.
    Base.metadata.create_all(bind=engine)

    from app.auth.routes import router as auth_router
    from app.exercises.routes import router as exercises_router
    from app.workouts.routes import router as workouts_router

    app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
    app.include_router(exercises_router, prefix="/api/exercises", tags=["exercises"])
    app.include_router(workouts_router, prefix="/api", tags=["workouts"])

    register_exception_handlers(app)

    @app.get("/api/health", tags=["meta"])
    def health() -> dict:
        """Liveness probe."""
        return ok({"status": "ok", "env": settings.env})

    return app


app = create_app()
