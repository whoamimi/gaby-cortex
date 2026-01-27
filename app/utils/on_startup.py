# app/utils/on_startup.py

from __future__ import annotations

import os
from functools import lru_cache

from .paths import (
    resolve_paths,
    DEFAULT_FASTAPI_APP_PATH,
    DEFAULT_FASTAPI_APP_PORT,
    DEFAULT_FASTAPI_APP_HOST
)
from .loader import Config, load_config
from .woodlogs import configure_logger

def run_checks_on_startup(ws: Config) -> None:
    """
    Production guardrails.
    """
    config_path = ws.dir.config_path

    if not ws.debug_mode:
        # Ensure prod isn't accidentally pointing at dev config folder
        if "dev" in config_path.as_posix().split("/"):
            raise EnvironmentError(
                f"debug_mode=False but config_path points to a dev directory: {config_path}"
            )

@lru_cache(maxsize=1)
def get_workspace() -> Config:
    """
    The main entrypoint for workspace setup. Called once on app startup and cached.
    """

    # Sets up environment variables and resolve paths
    paths = resolve_paths()

    # Read runtime app settings (env overrides)
    debug_mode = os.getenv("DEV_MODE", "true").strip().lower() == "true"
    app_path = os.getenv("FASTAPI_APP_PATH", DEFAULT_FASTAPI_APP_PATH)
    app_port = int(os.getenv("APP_PORT", str(DEFAULT_FASTAPI_APP_PORT)))
    app_host = os.getenv("APP_HOST", DEFAULT_FASTAPI_APP_HOST)

    # Load configuration from yaml files and configure workspace
    ws = load_config(
        paths,
        debug_mode=debug_mode,
        app_path=app_path,
        app_port=app_port,
        app_host=app_host,
    )
    run_checks_on_startup(ws)
    configure_logger(ws.debug_mode)

    return ws