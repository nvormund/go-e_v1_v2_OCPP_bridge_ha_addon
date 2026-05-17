#!/usr/bin/env sh
set -eu

OPTIONS_FILE="/data/options.json"
CONFIG_FILE="/data/bridge_config.yaml"

if [ ! -f "$OPTIONS_FILE" ]; then
  echo "Home Assistant options file not found: $OPTIONS_FILE" >&2
  exit 1
fi

python - <<'PY'
import json
from pathlib import Path

import yaml

options_path = Path("/data/options.json")
config_path = Path("/data/bridge_config.yaml")

options = json.loads(options_path.read_text(encoding="utf-8"))

config = {
    "goe": {
        "host": options["goe_host"],
        "api_version": options["goe_api_version"],
        "timeout_seconds": options["goe_timeout_seconds"],
        "poll_interval_seconds": options["goe_poll_interval_seconds"],
    },
    "ocpp": {
        "version": options["ocpp_version"],
        "backend_url": options["ocpp_backend_url"],
        "charge_point_id": options["ocpp_charge_point_id"],
        "connector_id": options["ocpp_connector_id"],
        "basic_auth_user": options.get("ocpp_basic_auth_user", ""),
        "basic_auth_password": options.get("ocpp_basic_auth_password", ""),
    },
    "bridge": {
        "dry_run": options["bridge_dry_run"],
        "read_only": options["bridge_read_only"],
        "allow_remote_start": options["bridge_allow_remote_start"],
        "allow_remote_stop": options["bridge_allow_remote_stop"],
        "heartbeat_interval_seconds": options["bridge_heartbeat_interval_seconds"],
        "meter_interval_seconds": options["bridge_meter_interval_seconds"],
        "reconnect_interval_seconds": options["bridge_reconnect_interval_seconds"],
        "websocket_ping_interval_seconds": options["bridge_websocket_ping_interval_seconds"],
        "websocket_ping_timeout_seconds": options["bridge_websocket_ping_timeout_seconds"],
        "log_level": options["bridge_log_level"],
        "state_file": options["bridge_state_file"],
        "log_file": options.get("bridge_log_file", ""),
    },
}

config_path.write_text(
    yaml.safe_dump(config, sort_keys=False, allow_unicode=False),
    encoding="utf-8",
)
PY

exec python -m goe_ocpp_bridge.main --config "$CONFIG_FILE"
