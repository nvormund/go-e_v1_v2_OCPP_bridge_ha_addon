from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum


class ChargerStatus(str, Enum):
    AVAILABLE = "Available"
    PREPARING = "Preparing"
    CHARGING = "Charging"
    SUSPENDED_EVSE = "SuspendedEVSE"
    FINISHING = "Finishing"
    FAULTED = "Faulted"
    UNAVAILABLE = "Unavailable"


@dataclass(frozen=True)
class MeterReading:
    timestamp: datetime
    energy_wh: float | None = None
    session_energy_wh: float | None = None
    power_w: float | None = None
    current_a: float | None = None
    voltage_v: float | None = None


@dataclass(frozen=True)
class ChargerSnapshot:
    status: ChargerStatus
    meter: MeterReading
    raw: dict


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
