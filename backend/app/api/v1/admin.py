from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.deps import DbSession, require_role
from app.models import Role, User
from app.schemas.admin import AdminStats, AuditOut
from app.schemas.common import Page
from app.services import admin as service

router = APIRouter(prefix="/admin", tags=["admin"])

Admin = Annotated[User, Depends(require_role(Role.ADMIN))]


@router.get("/audit", response_model=Page[AuditOut])
def audit_log(
    _: Admin,
    db: DbSession,
    action: Annotated[
        str | None, Query(max_length=64, description="Action prefix, e.g. certificate. or auth.")
    ] = None,
    date_from: Annotated[date | None, Query(description="Inclusive, UTC.")] = None,
    date_to: Annotated[date | None, Query(description="Inclusive, UTC.")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Page[AuditOut]:
    items, total = service.list_audit(
        db, action=action, date_from=date_from, date_to=date_to, page=page, size=size
    )
    return Page[AuditOut](
        items=[AuditOut.model_validate(row) for row in items], total=total, page=page, size=size
    )


@router.get("/stats", response_model=AdminStats)
def stats(_: Admin, db: DbSession) -> AdminStats:
    return AdminStats.model_validate(service.stats(db))
