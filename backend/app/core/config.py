from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: str = "dev"
    log_level: str = "INFO"
    api_v1_prefix: str = "/api/v1"
    cors_origins: str = "http://localhost:5173"

    database_url: str = "postgresql+psycopg://ava:ava@localhost:5432/ava"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 15
    refresh_token_days: int = 7

    keys_dir: str = "/keys"

    upload_dir: str = "/data/uploads"
    upload_max_mb: int = 10
    upload_retention_days: int = 7

    # Issued certificate PDFs. Written once, served as-is, never pruned by the
    # upload-retention job (which only touches verifier uploads).
    issued_dir: str = "/data/uploads/certificates"

    import_max_rows: int = 5000
    import_max_mb: int = 2

    ocr_min_field_confidence: float = 0.85
    name_match_threshold: int = 90
    name_conflict_threshold: int = 75

    share_link_ttl_hours: int = 72

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
