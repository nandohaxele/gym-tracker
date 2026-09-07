"""Templates HTTP routes.

All endpoints require JWT authentication and are scoped to globals plus the
caller's personal templates.

Endpoints (mounted under /api by main.py):
    GET    /templates
    POST   /templates
    POST   /templates/resolve
    GET    /templates/{template_id}
    PATCH  /templates/{template_id}
    DELETE /templates/{template_id}
    POST   /templates/{template_id}/personalize
    POST   /templates/{template_id}/start
"""

from fastapi import APIRouter, Body, Depends, status
from sqlalchemy.orm import Session

from app.auth.models import User
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.response import ok
from app.templates import service
from app.templates.schemas import (
    TemplateCreate,
    TemplateDetail,
    TemplateNameIn,
    TemplateResolveIn,
    TemplateResolveOut,
    TemplateSummary,
    TemplateUpdate,
)
from app.workouts.schemas import WorkoutDetail


router = APIRouter()


@router.get("/templates")
def list_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """List global templates plus the caller's personal ones."""
    items = service.list_templates(db, current_user.id)
    return ok([TemplateSummary.model_validate(item) for item in items])


@router.post("/templates", status_code=status.HTTP_201_CREATED)
def create_template(
    payload: TemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Create a personal template owned by the caller."""
    template = service.create_personal_template(db, current_user.id, payload)
    return ok(TemplateDetail.model_validate(template))


@router.post("/templates/resolve")
def resolve_template(
    payload: TemplateResolveIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Resolve an exact normalized template name visible to the caller."""
    result = service.resolve_template(
        db, current_user.id, payload.query, scope=payload.scope
    )
    template = (
        TemplateSummary.model_validate(result.template)
        if result.template is not None
        else None
    )
    candidates = (
        [TemplateSummary.model_validate(item) for item in result.candidates]
        if result.ambiguous
        else []
    )
    return ok(
        TemplateResolveOut(
            status=result.status,
            query=result.query,
            normalized=result.normalized,
            scope=result.scope,
            level=result.level.value if result.level is not None else None,
            template=template,
            candidates=candidates,
        )
    )


@router.get("/templates/{template_id}")
def get_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Fetch a visible template with its nested target tree."""
    template = service.get_template(db, current_user.id, template_id)
    return ok(TemplateDetail.model_validate(template))


@router.patch("/templates/{template_id}")
def update_template(
    template_id: int,
    payload: TemplateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Update one of the caller's personal templates."""
    template = service.update_personal_template(
        db, current_user.id, template_id, payload
    )
    return ok(TemplateDetail.model_validate(template))


@router.delete("/templates/{template_id}")
def delete_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Delete a personal template. Started Sessions keep their snapshot."""
    service.delete_personal_template(db, current_user.id, template_id)
    return ok(None)


@router.post(
    "/templates/{template_id}/personalize",
    status_code=status.HTTP_201_CREATED,
)
def personalize_template(
    template_id: int,
    payload: TemplateNameIn | None = Body(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Copy a global template into a new personal template."""
    name = payload.name if payload is not None else None
    template = service.personalize_template(
        db, current_user.id, template_id, name=name
    )
    return ok(TemplateDetail.model_validate(template))


@router.post(
    "/templates/{template_id}/start",
    status_code=status.HTTP_201_CREATED,
)
def start_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Create an independent Session snapshot from a visible template."""
    workout = service.start_template(db, current_user.id, template_id)
    return ok(WorkoutDetail.model_validate(workout))
