"""Test fixtures. Tests run against a separate `<db>_test` Postgres database so
they never touch demo/seed data. Each test runs inside a transaction that is
rolled back afterwards."""

from collections.abc import Iterator
from pathlib import Path
from typing import Annotated

import pytest
from fastapi import APIRouter, Depends
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import Base, get_db
from app.core.deps import require_role
from app.core.security import hash_password
from app.main import app
from app.models import Institution, Role, User
from app.services.signing import load_or_create_private_key, public_key_pem

PASSWORD = "Correct-Horse-1"


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    url = make_url(settings.database_url)
    test_db = f"{url.database}_test"

    admin_engine = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        exists = conn.scalar(text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": test_db})
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{test_db}"'))
    admin_engine.dispose()

    eng = create_engine(url.set(database=test_db))
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture
def db(engine: Engine) -> Iterator[Session]:
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


# A route that only admins may call, used to test role blocking without
# depending on admin features that are not built yet.
_test_router = APIRouter()


@_test_router.get("/_test/admin-only")
def _admin_only(_: Annotated[User, Depends(require_role(Role.ADMIN))]) -> dict[str, bool]:
    return {"ok": True}


app.include_router(_test_router)


@pytest.fixture
def client(db: Session) -> Iterator[TestClient]:
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def keys_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Signing keys go to a per-test temp dir, never the real KEYS_DIR."""
    path = tmp_path / "keys"
    monkeypatch.setattr(settings, "keys_dir", str(path))
    return path


@pytest.fixture(autouse=True)
def issued_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Issued certificate PDFs go to a per-test temp dir, never the real volume."""
    path = tmp_path / "issued"
    monkeypatch.setattr(settings, "issued_dir", str(path))
    return path


def make_institution(db: Session, code: str, name: str) -> Institution:
    key = load_or_create_private_key(code)
    inst = Institution(name=name, code=code, public_key=public_key_pem(key))
    db.add(inst)
    db.flush()
    return inst


@pytest.fixture
def users(db: Session) -> dict[str, User]:
    inst = make_institution(db, "TST", "Test Institute (fictional)")
    other = make_institution(db, "OTH", "Other Institute (fictional)")
    created = {
        "admin": User(email="admin@t.test", role="admin"),
        "institution": User(email="inst@t.test", role="institution", institution_id=inst.id),
        "other_institution": User(
            email="other@t.test", role="institution", institution_id=other.id
        ),
        "verifier": User(email="verifier@t.test", role="verifier"),
        "inactive": User(email="gone@t.test", role="verifier", is_active=False),
    }
    pw_hash = hash_password(PASSWORD)
    for u in created.values():
        u.password_hash = pw_hash
        db.add(u)
    db.flush()
    return created


@pytest.fixture
def auth_headers(client: TestClient, users: dict[str, User]) -> dict[str, dict[str, str]]:
    """Bearer headers per user key in `users`, e.g. auth_headers["institution"]."""
    out = {}
    for name, user in users.items():
        if not user.is_active:
            continue
        r = client.post("/api/v1/auth/login", json={"email": user.email, "password": PASSWORD})
        out[name] = {"Authorization": f"Bearer {r.json()['access_token']}"}
    return out
