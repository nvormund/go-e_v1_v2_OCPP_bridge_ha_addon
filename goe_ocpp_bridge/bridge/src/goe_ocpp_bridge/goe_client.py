from __future__ import annotations

import abc
from typing import Any

from .models import ChargerSnapshot


class GoeClient(abc.ABC):
    @abc.abstractmethod
    async def close(self) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def get_snapshot(self) -> ChargerSnapshot:
        raise NotImplementedError

    @abc.abstractmethod
    async def start_charging(self) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def stop_charging(self) -> None:
        raise NotImplementedError


def normalize_host(host: str) -> str:
    host = host.strip().rstrip("/")
    if host.startswith("http://") or host.startswith("https://"):
        return host
    return f"http://{host}"


def number_or_none(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def nrg_value(nrg: list, index: int) -> float | None:
    if len(nrg) <= index:
        return None
    return number_or_none(nrg[index])


def nrg_current_a(nrg: list) -> float | None:
    currents = [value / 10 for value in (nrg_value(nrg, index) for index in (4, 5, 6)) if value]
    if not currents:
        return None
    return max(currents)


def nrg_power_w(nrg: list) -> float | None:
    total_power = nrg_value(nrg, 11)
    if total_power is not None:
        return total_power * 10
    phase_powers = [value * 100 for value in (nrg_value(nrg, index) for index in (7, 8, 9)) if value]
    if phase_powers:
        return sum(phase_powers)
    return None
