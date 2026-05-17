from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class BridgeState:
    last_status: str | None = None
    active_transaction_id: int | None = None
    active_id_tag: str | None = None
    transaction_start_meter_wh: float | None = None
    transaction_start_session_wh: float | None = None
    last_meter_wh: float | None = None


class StateStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def load(self) -> BridgeState:
        if not self.path.exists():
            return BridgeState()
        data = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"State file must contain a JSON object: {self.path}")
        return BridgeState(**{k: data.get(k) for k in BridgeState.__dataclass_fields__})

    def save(self, state: BridgeState) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp_path.write_text(json.dumps(asdict(state), indent=2, sort_keys=True), encoding="utf-8")
        tmp_path.replace(self.path)
