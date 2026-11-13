"""Admin management of institutions and their signing keys."""

import secrets

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import hash_password
from app.models import Certificate, Institution, Role, User
from app.services import audit
from app.services.signing import load_or_create_private_key, private_key_path, public_key_pem

# Unambiguous alphabet: no O/0, l/1 — the password is read off a screen once.
_PASSWORD_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"
PASSWORD_LENGTH = 16


def generate_password(length: int = PASSWORD_LENGTH) -> str:
    return "".join(secrets.choice(_PASSWORD_ALPHABET) for _ in range(length))


def _with_counts(db: Session, institutions: list[Institution]) -> list[Institution]:
    """Attach certificate_count and user_count for the response. They are plain
    attributes, not columns, so nothing is written back."""
    ids = [i.id for i in institutions]
    if not ids:
        return institutions

    certificates = dict(
        db.execute(
            select(Certificate.institution_id, func.count())
            .where(Certificate.institution_id.in_(ids))
            .group_by(Certificate.institution_id)
        ).all()
    )
    users = dict(
        db.execute(
            select(User.institution_id, func.count())
            .where(User.institution_id.in_(ids))
            .group_by(User.institution_id)
        ).all()
    )
    for institution in institutions:
        institution.certificate_count = certificates.get(institution.id, 0)  # type: ignore[attr-defined]
        institution.user_count = users.get(institution.id, 0)  # type: ignore[attr-defined]
    return institutions


def list_institutions(db: Session, *, page: int, size: int) -> tuple[list[Institution], int]:
    stmt = select(Institution)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = list(
        db.scalars(stmt.order_by(Institution.code).offset((page - 1) * size).limit(size)).all()
    )
    return _with_counts(db, items), total


def get_institution(db: Session, institution_id: int) -> Institution:
    institution = db.get(Institution, institution_id)
    if institution is None:
        raise AppError(404, "not_found", "Institution not found.")
    return _with_counts(db, [institution])[0]


def create_institution(
    db: Session, actor: User, *, name: str, code: str, admin_email: str
) -> tuple[Institution, User, str]:
    """Create the institution, its Ed25519 keypair and its first user.

    Returns the generated password; it is hashed immediately and never stored
    or logged in plain text, so this is the only chance to show it.
    """
    if db.scalar(select(Institution.id).where(Institution.code == code)):
        raise AppError(409, "duplicate_code", f"An institution with code {code} already exists.")
    if db.scalar(select(User.id).where(User.email == admin_email)):
        raise AppError(409, "duplicate_email", "A user with this email already exists.")

    key = load_or_create_private_key(code)
    institution = Institution(name=name, code=code, public_key=public_key_pem(key))
    db.add(institution)
    db.flush()

    password = generate_password()
    user = User(
        email=admin_email,
        password_hash=hash_password(password),
        role=Role.INSTITUTION.value,
        institution_id=institution.id,
    )
    db.add(user)
    db.flush()

    audit.record(
        db,
        actor_id=actor.id,
        action="institution.create",
        entity="institution",
        entity_id=str(institution.id),
        meta={"code": institution.code, "key_file": str(private_key_path(code).name)},
    )
    audit.record(
        db,
        actor_id=actor.id,
        action="user.create",
        entity="user",
        entity_id=str(user.id),
        meta={"role": user.role, "institution_code": institution.code},
    )
    try:
        db.commit()
    except IntegrityError as exc:  # lost a race on the code or the email
        db.rollback()
        raise AppError(409, "duplicate_code", "That code or email was just taken.") from exc

    db.refresh(institution)
    db.refresh(user)
    return _with_counts(db, [institution])[0], user, password


def update_institution(
    db: Session, actor: User, institution_id: int, *, name: str | None, is_active: bool | None
) -> Institution:
    institution = db.get(Institution, institution_id)
    if institution is None:
        raise AppError(404, "not_found", "Institution not found.")

    changed: dict[str, object] = {}
    if name is not None and name != institution.name:
        institution.name = name
        changed["name"] = name
    if is_active is not None and is_active != institution.is_active:
        institution.is_active = is_active
        changed["is_active"] = is_active

    if changed:
        audit.record(
            db,
            actor_id=actor.id,
            action="institution.update",
            entity="institution",
            entity_id=str(institution.id),
            meta={"code": institution.code, **changed},
        )
        db.commit()
        db.refresh(institution)
    return _with_counts(db, [institution])[0]


def delete_institution(db: Session, actor: User, institution_id: int) -> None:
    """Only an institution that never issued anything can be removed. One with
    certificates is deactivated instead, so issued credentials stay verifiable."""
    institution = db.get(Institution, institution_id)
    if institution is None:
        raise AppError(404, "not_found", "Institution not found.")

    certificates = db.scalar(
        select(func.count())
        .select_from(Certificate)
        .where(Certificate.institution_id == institution.id)
    )
    if certificates:
        raise AppError(
            409,
            "institution_has_certificates",
            f"{institution.code} has {certificates} certificate(s). "
            "Deactivate it instead so its certificates stay verifiable.",
        )

    code = institution.code
    users = list(db.scalars(select(User).where(User.institution_id == institution.id)))
    audit.record(
        db,
        actor_id=actor.id,
        action="institution.delete",
        entity="institution",
        entity_id=str(institution.id),
        meta={"code": code, "users_removed": len(users)},
    )
    for user in users:
        db.delete(user)
    db.delete(institution)
    try:
        db.commit()
    except IntegrityError as exc:
        # A user who already acted is referenced by the audit log, which is
        # append-only — the institution stays and should be deactivated.
        db.rollback()
        raise AppError(
            409,
            "institution_in_use",
            f"{code} cannot be removed because its activity is on the audit trail. "
            "Deactivate it instead.",
        ) from exc
