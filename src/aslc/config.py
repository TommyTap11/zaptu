"""Runtime configuration from environment."""

from __future__ import annotations

import logging
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

_log = logging.getLogger("zaptu.config")


def _bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _resolve_data_dir() -> Path:
    """Prefer ZAPTU_DATA_DIR, then DATA_DIR, then ./data. Never crash if unwritable."""
    raw = os.getenv("ZAPTU_DATA_DIR") or os.getenv("DATA_DIR") or "./data"
    candidates = [Path(raw)]
    if not candidates[0].is_absolute():
        candidates.append(Path.cwd() / raw)
    candidates.append(Path(tempfile.gettempdir()) / "zaptu-data")

    for path in candidates:
        try:
            path = path.resolve()
            path.mkdir(parents=True, exist_ok=True)
            probe = path / ".write_probe"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            return path
        except OSError as exc:
            _log.warning("data_dir %s not usable (%s); trying next", path, exc)
    # Last resort: return /tmp path even if probe failed (storage will no-op writes)
    return Path(tempfile.gettempdir()) / "zaptu-data"


@dataclass
class Settings:
    host: str = field(default_factory=lambda: os.getenv("HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(os.getenv("PORT", "8000")))
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    api_token: str | None = field(default_factory=lambda: os.getenv("API_TOKEN") or None)
    webhook_url: str | None = field(
        default_factory=lambda: os.getenv("LEAD_WEBHOOK_URL") or None
    )
    webhook_token: str | None = field(
        default_factory=lambda: os.getenv("LEAD_WEBHOOK_TOKEN") or None
    )
    data_dir: Path = field(default_factory=_resolve_data_dir)
    # Mock is OFF unless explicitly enabled (ZAPTU_MOCK_FORWARDER or legacy MOCK_FORWARDING).
    mock_forwarding: bool = field(
        default_factory=lambda: _bool("ZAPTU_MOCK_FORWARDER", False)
        or _bool("MOCK_FORWARDING", False)
    )
    require_consent: bool = field(default_factory=lambda: _bool("REQUIRE_CONSENT", True))
    public_base_url: str = field(
        default_factory=lambda: os.getenv("PUBLIC_BASE_URL", "http://localhost:8000")
    )
    cors_origins: tuple[str, ...] = field(
        default_factory=lambda: tuple(
            o.strip()
            for o in os.getenv(
                "CORS_ORIGINS", "https://zaptu.ai,https://www.zaptu.ai"
            ).split(",")
            if o.strip()
        )
    )
    rate_limit_per_minute: int = field(
        default_factory=lambda: int(os.getenv("RATE_LIMIT_PER_MINUTE", "30"))
    )
    thanks_url: str = field(
        default_factory=lambda: os.getenv("THANKS_URL", "https://zaptu.ai/thanks/")
    )


settings = Settings()
