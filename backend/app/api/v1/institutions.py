from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.core.deps import DbSession, require_role
from app.models import Institution, Role, User
from app.schemas.common import Page
from app.schemas.institutions import (
    InstitutionCreate,
    InstitutionCreated,
    InstitutionOut,
    InstitutionUpdate,
)
from app.services import institutions as service

router = APIRouter(prefix="/institutions", tags=["institutions"])

Admin = Annotated[User, Depends(require_role(Role.ADMIN))]


@router.post("", response_model=InstitutionCreated, status_code=status.HTTP_201_CREATED)
def create_institution(body: InstitutionCreate, user: Admin, db: DbSession) -> InstitutionCreated:
    """Create an institution, generate its Ed25519 keypair (private key to
    KEYS_DIR, public key to the row) and its first user. The generated password
    is returned once and never again."""
    institution, created_user, password = service.create_institution(
        db, user, name=body.name, code=body.code, admin_email=body.admin_email
    )
    return InstitutionCreated(
        institution=InstitutionOut.model_validate(institution),
        user=created_user,  # type: ignore[arg-type]
        password=password,
    )


@router.get("", response_model=Page[InstitutionOut])
def list_institutions(
    _: Admin,
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Page[InstitutionOut]:
    items, total = service.list_institutions(db, page=page, size=size)
    return Page[InstitutionOut](
        items=[InstitutionOut.model_validate(i) for i in items], total=total, page=page, size=size
    )


@router.get("/{institution_id}", response_model=InstitutionOut)
def get_institution(institution_id: int, _: Admin, db: DbSession) -> Institution:
    return service.get_institution(db, institution_id)


@router.patch("/{institution_id}", response_model=InstitutionOut)
def update_institution(
    institution_id: int, body: InstitutionUpdate, user: Admin, db: DbSession
) -> Institution:
    """Name and active flag only — the code and key are what signatures refer to."""
    return service.update_institution(
        db, user, institution_id, name=body.name, is_active=body.is_active
    )


@router.delete(
    "/{institution_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={409: {"description": "The institution has certificates; deactivate it instead"}},
)
def delete_institution(institution_id: int, user: Admin, db: DbSession) -> Response:
    service.delete_institution(db, user, institution_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
