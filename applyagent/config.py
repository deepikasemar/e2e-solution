"""Runtime settings. Secrets come from the environment, never from source."""

from __future__ import annotations

import os
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = Path(__file__).resolve().parent

TZ = ZoneInfo("Asia/Kolkata")

# Weights from section 5.6.3. They are rescaled to sum to 1 if edited.
DEFAULT_WEIGHTS = {"skill": 0.50, "semantic": 0.35, "preference": 0.15}

MANUAL_MINUTES = 90
REVIEW_MINUTES = 8
DAILY_LIMIT_DEFAULT = 8


def database_path() -> Path:
    raw = os.environ.get("DATABASE_PATH", str(ROOT / "var" / "applyagent.sqlite"))
    return Path(raw)


def daily_limit() -> int:
    try:
        value = int(os.environ.get("DAILY_LIMIT", str(DAILY_LIMIT_DEFAULT)))
    except ValueError:
        return DAILY_LIMIT_DEFAULT
    return max(1, value)


def secret_key() -> str:
    return os.environ.get("SECRET_KEY", "applyagent-local-dev")


def semantic_backend() -> str:
    return os.environ.get("SEMANTIC_BACKEND", "tfidf").strip().lower() or "tfidf"
