"""Runtime configuration from environment."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    api_token: str | None = os.getenv("API_TOKEN") or None
    webhook_url: str | None = os.getenv("LEAD_WEBHOOK_URL") or None
    webhook_token: str | None = os.getenv("LEAD_WEBHOOK_TOKEN") or None
    data_dir: Path = Path(os.getenv("DATA_DIR", "data")).resolve()
    mock_forwarding: bool = _bool("MOCK_FORWARDING", True)
    require_consent: bool = _bool("REQUIRE_CONSENT", True)
    public_base_url: str = os.getenv("PUBLIC_BASE_URL", "http://localhost:8000")


settings = Settings()
settings.data_dir.mkdir(parents=True, exist_ok=True)
