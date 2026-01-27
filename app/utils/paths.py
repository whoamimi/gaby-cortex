# app/utils/paths.py
# Set up and resolve important filesystem paths for the application.

from __future__ import annotations

import os
from pathlib import Path
from dataclasses import dataclass
from .woodlogs import setup_logger

log = setup_logger(__name__)

DEFAULT_APP_ROOT_PATH = "backend-v2"
DEFAULT_REL_FILE_PATH = f"{DEFAULT_APP_ROOT_PATH}/app/utils/setup.py"
DEFAULT_APP_HANDLER = "app"

DEFAULT_FASTAPI_APP_PATH = "app.main:app"
DEFAULT_FASTAPI_APP_PORT = 8005
DEFAULT_FASTAPI_APP_HOST = "0.0.0.0"
REQUIRED_CONFIG_FILES = [
    "options.yml",
    "agent.yml"
]

@dataclass(frozen=True)
class WorkspacePaths:
    root_app_path: Path
    app_path: Path
    config_path: Path
    src_path: Path
    api_path: Path
    utils_path: Path
    static_path: Path

def _load_dotenv_if_present(root_app_path: Path) -> None:
    """
    Load .env only when running in dev and the file exists.
    In prod, environment variables should come from the runtime environment.
    """
    env_file = root_app_path / ".env"

    if env_file.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(env_file)
            log.info("Loaded environment variables from %s", env_file)
        except Exception as e:
            # In dev you typically want to see this; in prod you typically won't call this path.
            raise RuntimeError(f"Failed loading .env from {env_file}: {e}") from e
    else:
        log.info(".env file not found at %s; skipping load. Defaulting to sys variables and assuming run for prod.")

def resolve_paths() -> WorkspacePaths:
    """
      - app_path  = .../app
      - root_path = .../(project root)
    """

    this_file = Path(__file__).resolve()
    app_path = this_file.parents[1]          # .../app
    root_app_path = this_file.parents[2]     # .../(project root)
    log.info("Running from file %s \nroot_app_path=%s \nResolved app_path=%s ", this_file, root_app_path, app_path)

    _load_dotenv_if_present(root_app_path)
    dev_mode = os.getenv("DEV_MODE", "true").strip().lower() == "true"

    return WorkspacePaths(
        root_app_path=root_app_path,
        app_path=app_path,
        config_path=app_path / "config" / ("dev" if dev_mode else "prod"),
        src_path=app_path / "src",
        api_path=app_path / "api",
        utils_path=app_path / "utils",
        static_path=app_path / "static",
    )

