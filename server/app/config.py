from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        extra="ignore"
    )

    database_url: str = Field(default="sqlite:///./exam.db")

    server_host: str = "0.0.0.0"
    server_port: str = "8000"
    app_env: str = "development"
    debug: bool = False

    secret_key: str = "change-me"
    acess_token_expire_minutes: int = 720
    algorithm: str = "HS256"

    default_admin_username: str = "admin"
    default_admin_password: str = "admin12345"

    storage_path: str = "./storage"
    max_uploaded_size_mb: int = 50

    default_exam_duration_minutes: int = 235

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def storage_dir(self) -> Path:
        p = Path(self.storage_path)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def task_files_dir(self) -> Path:
        p = self.storage_dir / "task_files"
        p.mkdir(parents=True, exist_ok=True)
        return p


@lru_cache
def get_settings() -> Settings:
    return Settings()
