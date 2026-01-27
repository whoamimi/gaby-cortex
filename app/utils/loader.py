# app/utils/loader.py
# Loads configuration yaml files from config directory on setup / startup

from __future__ import annotations

import os
import yaml
from typing import Any
from pathlib import Path
from dataclasses import dataclass, field

from .paths import REQUIRED_CONFIG_FILES, WorkspacePaths
from .woodlogs import setup_logger

log = setup_logger(__name__)

@dataclass
class AgentConfig:
    dataIngestion: dict = field(default_factory=dict)
    dataCleaning: dict = field(default_factory=dict)
    dataAnalytics: dict = field(default_factory=dict)
    dataQuality: dict = field(default_factory=dict)

@dataclass(frozen=True)
class SocketConfig:
    dataTypes: list[str]
    databaseTypes: list[str]
    dataPlatformTypes: list[str]
    eventStages: list[str]

@dataclass(frozen=True)
class Secrets:
    jupyter_kernel_server_url: str
    jupyter_kernel_server_timeout: int
    jupyter_kernel_server_socket: str
    _hf_token: str
    _jupyter_kernel_server_key: str
    _genai_api_key: str
    google_project_id: str
    google_project_app_name: str
    google_project_number: str
    google_cloud_location: str

    @property
    def project_name(self) -> str:
        return f"projects/{self.google_project_number}"

@dataclass(frozen=True)
class Config:
    dir: WorkspacePaths
    agent: AgentConfig
    socket: SocketConfig
    debug_mode: bool
    app_path: str
    app_port: int
    app_host: str
    secrets: Secrets

def _load_yaml_lists(yaml_file: Path) -> dict[str, list[str]]:
    """
    Loads YAML and ensures each top-level key maps to a list[str].
    If a key is missing or not a list, it becomes [].
    """
    try:
        data = yaml.safe_load(yaml_file.read_text()) or {}

        if not isinstance(data, dict):
            raise ValueError("Top-level YAML content must be a mapping/dict.")

        out: dict[str, list[str]] = {}
        for key, val in data.items():
            if isinstance(val, list):
                out[key] = [str(x) for x in val]
            else:
                out[key] = []

        return out

    except Exception as e:
        raise RuntimeError(f"Error loading YAML file {yaml_file}: {e}") from e

def load_agent_config(file_path: Path) -> AgentConfig:
    """
    Load AgentConfig from agent.yml file.
    """
    try:
        data = yaml.safe_load(file_path.read_text()) or {}

        if not isinstance(data, dict):
            raise ValueError("Top-level YAML content must be a mapping/dict.")

        services = {}
        for service_name, service_config_path in data.items():

            if service_config_path is not None:
                full_service_path = file_path.parent / service_config_path

                log.info("Loading agent service config for %s from %s", service_name, full_service_path)

                if full_service_path.exists():
                    service_data = yaml.safe_load(full_service_path.read_text()) or {}
                    log.debug(f"Loaded config for {service_name} from {full_service_path}")
                    services[service_name] = service_data

        return AgentConfig(
            dataIngestion=services.get("data-ingestion", {}),
            dataCleaning=services.get("data-cleaning", {}),
            dataAnalytics=services.get("data-analytics", {}),
            dataQuality=services.get("data-quality", {}),
        )

    except Exception as e:
        raise RuntimeError(f"Error loading AgentConfig from {file_path}: {e}") from e

def load_streaming_config(schema_file: Path) -> SocketConfig:
    """
    Load SocketConfig.
    """
    try:
        data = _load_yaml_lists(schema_file)

        return SocketConfig(
            dataTypes=data.get("dataTypes", []),
            databaseTypes=data.get("databaseTypes", []),
            dataPlatformTypes=data.get("dataPlatformTypes", []),
            eventStages=data.get("eventStages", [])
        )

    except Exception as e:
        raise RuntimeError(f"Error loading SocketConfig from {schema_file}: {e}") from e

def load_config(paths: Any, *, debug_mode: bool, app_path: str, app_port: int, app_host: str) -> Config:
    """
    Load the main application configuration from the config directory.
    """

    config_dir = paths.config_path
    schema_file = config_dir / "options.yml"
    agent_file = config_dir / "agent.yml"
    
    # Ensure all required config files exists
    missing = [name for name in REQUIRED_CONFIG_FILES if not (config_dir / name).exists()]
    if missing:
        raise FileNotFoundError(
            f"Production config folder is missing required files: {missing}. Path: {config_dir}"
        )

    # Load configurations respective to their supporting domains
    agent_config = load_agent_config(agent_file)
    socket_config = load_streaming_config(schema_file)

    return Config(
        dir=paths,
        agent=agent_config,
        socket=socket_config,
        debug_mode=debug_mode,
        app_path=app_path,
        app_port=app_port,
        app_host=app_host,
        secrets=Secrets(
                jupyter_kernel_server_url=os.getenv("JUPYTER_KERNEL_SERVER", ""),
                jupyter_kernel_server_timeout=int(os.getenv("JUPYTER_KERNEL_SERVER_TIMEOUT", 10)),
                jupyter_kernel_server_socket=os.getenv("JUPYTER_KERNEL_SERVER_SOCKET", ""),
                _hf_token=os.getenv("HF_TOKEN", ""),
                _jupyter_kernel_server_key=os.getenv("JUPYTER_KERNEL_SERVER_KEY", ""),
                _genai_api_key=os.getenv("GENAI_API_KEY", ""),
                google_cloud_location=os.getenv("GOOGLE_CLOUD_LOCATION", ""),
                google_project_id=os.getenv("GOOGLE_PROJECT_ID", ""),
                google_project_app_name=os.getenv("GOOGLE_PROJECT_APP_NAME", ""),
                google_project_number=os.getenv("GOOGLE_PROJECT_NUMBER", "")
            )
        )
