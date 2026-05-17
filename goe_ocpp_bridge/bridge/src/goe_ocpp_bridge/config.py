from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class GoeConfig:
    host: str
    api_version: str = "auto"
    timeout_seconds: float = 5
    poll_interval_seconds: float = 30


@dataclass(frozen=True)
class OcppConfig:
    version: str = "1.6"
    backend_url: str = ""
    charge_point_id: str = ""
    connector_id: int = 1
    basic_auth_user: str = ""
    basic_auth_password: str = ""


@dataclass(frozen=True)
class BridgeConfig:
    dry_run: bool = True
    read_only: bool = True
    allow_remote_start: bool = False
    allow_remote_stop: bool = True
    heartbeat_interval_seconds: float = 60
    meter_interval_seconds: float = 30
    reconnect_interval_seconds: float = 10
    websocket_ping_interval_seconds: float = 20
    websocket_ping_timeout_seconds: float = 20
    log_level: str = "INFO"
    state_file: str = "state.json"
    log_file: str = ""


@dataclass(frozen=True)
class AppConfig:
    goe: GoeConfig
    ocpp: OcppConfig
    bridge: BridgeConfig
    base_dir: Path


def _require_mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"Section '{name}' must be a mapping.")
    return value


def load_config(path: str | Path = "config.yaml") -> AppConfig:
    config_path = Path(path).expanduser().resolve()
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    root = _require_mapping(data, "root")
    goe_data = _require_mapping(root.get("goe", {}), "goe")
    ocpp_data = _require_mapping(root.get("ocpp", {}), "ocpp")
    bridge_data = _require_mapping(root.get("bridge", {}), "bridge")

    goe = GoeConfig(**goe_data)
    ocpp = OcppConfig(**ocpp_data)
    bridge = BridgeConfig(**bridge_data)

    if goe.api_version not in {"auto", "v1", "v2"}:
        raise ValueError("goe.api_version must be one of: auto, v1, v2")
    if ocpp.version != "1.6":
        raise ValueError("Only OCPP 1.6 is supported.")
    if not ocpp.backend_url:
        raise ValueError("ocpp.backend_url is required.")
    if not ocpp.charge_point_id:
        raise ValueError("ocpp.charge_point_id is required.")
    if ocpp.connector_id < 1:
        raise ValueError("ocpp.connector_id must be >= 1.")

    return AppConfig(goe=goe, ocpp=ocpp, bridge=bridge, base_dir=config_path.parent)
