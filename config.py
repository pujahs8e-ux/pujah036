"""Central configuration: paths + environment variables."""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

STATIC_DIR = BASE_DIR / "static"
PANELS_DIR = STATIC_DIR / "panels"
EXPORTS_DIR = STATIC_DIR / "exports"
FONTS_DIR = STATIC_DIR / "fonts"
TEMPLATES_DIR = BASE_DIR / "templates"

for folder in (PANELS_DIR, EXPORTS_DIR, FONTS_DIR):
    folder.mkdir(parents=True, exist_ok=True)


def _env_bool(name: str, default: bool = False) -> bool:
    return (
        os.getenv(name, str(default))
        .strip()
        .lower()
        in {"1", "true", "yes", "on"}
    )


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

HF_TOKEN = (
    os.getenv("HF_API_KEY")
    or os.getenv("HF_TOKEN")
    or ""
).strip()

GEMINI_FLASH_MODEL = os.getenv("GEMINI_FLASH_MODEL", "gemini-1.5-flash").strip()
GEMINI_PRO_MODEL = os.getenv("GEMINI_PRO_MODEL", "gemini-1.5-pro").strip()

SD_MODEL_ID = os.getenv("SD_MODEL_ID", "black-forest-labs/FLUX.1-schnell").strip()

USE_PLACEHOLDER_IMAGES = _env_bool("USE_PLACEHOLDER_IMAGES", False)
IMAGE_STEPS = _env_int("IMAGE_STEPS", 25)
IMAGE_SIZE = _env_int("IMAGE_SIZE", 512)

NUM_PANELS = 5


def rel_path(path: Path) -> str:
    return Path(path).resolve().relative_to(BASE_DIR).as_posix() 