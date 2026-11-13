from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, func, true
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Institution(Base):
    __tablename__ = "institutions"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    # Ed25519 public key, PEM (SubjectPublicKeyInfo). Private key lives in KEYS_DIR.
    public_key: Mapped[str] = mapped_column(Text)
    # Deactivated institutions keep their records and stay verifiable; their
    # users can no longer sign in. Used instead of deleting a live registry.
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=true(), default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
