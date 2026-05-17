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
config_path.write_text(
    yaml.safe_dump(options, sort_keys=False, allow_unicode=False),
    encoding="utf-8",
)
PY

exec python -m goe_ocpp_bridge.main --config "$CONFIG_FILE"
