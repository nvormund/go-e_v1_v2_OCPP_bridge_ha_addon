from __future__ import annotations

import logging

import aiohttp

from .config import GoeConfig
from .goe_client import GoeClient, normalize_host, nrg_current_a, nrg_power_w, number_or_none
from .models import ChargerSnapshot, ChargerStatus, MeterReading, utc_now

LOGGER = logging.getLogger(__name__)


class GoeV2Client(GoeClient):
    def __init__(self, config: GoeConfig):
        self.base_url = normalize_host(config.host)
        timeout = aiohttp.ClientTimeout(total=config.timeout_seconds)
        self.session = aiohttp.ClientSession(timeout=timeout)

    async def close(self) -> None:
        await self.session.close()

    async def get_snapshot(self) -> ChargerSnapshot:
        async with self.session.get(f"{self.base_url}/api/status") as response:
            response.raise_for_status()
            data = await response.json(content_type=None)
        return parse_v2_status(data)

    async def start_charging(self) -> None:
        await self._set("alw", "1")

    async def stop_charging(self) -> None:
        await self._set("alw", "0")

    async def _set(self, key: str, value: str) -> None:
        async with self.session.get(f"{self.base_url}/api/set", params={key: value}) as response:
            response.raise_for_status()
            LOGGER.debug("go-e v2 set %s=%s returned %s", key, value, response.status)


def parse_v2_status(data: dict) -> ChargerSnapshot:
    car_state = str(data.get("car", "0"))
    allow = str(data.get("alw", "0"))
    error = str(data.get("err", "0"))
    if error not in {"0", "None", "none", ""}:
        status = ChargerStatus.FAULTED
    elif car_state == "2" and allow == "1":
        status = ChargerStatus.CHARGING
    elif car_state in {"1", "2"}:
        status = ChargerStatus.PREPARING
    else:
        status = ChargerStatus.AVAILABLE

    nrg = data.get("nrg") if isinstance(data.get("nrg"), list) else []
    voltage = number_or_none(nrg[0]) if len(nrg) > 0 else None
    energy_wh = number_or_none(data.get("eto")) or number_or_none(data.get("wh"))
    power_w = number_or_none(data.get("pwr")) or nrg_power_w(nrg)
    current_a = nrg_current_a(nrg) or number_or_none(data.get("acu")) or number_or_none(data.get("amp"))

    return ChargerSnapshot(
        status=status,
        meter=MeterReading(
            timestamp=utc_now(),
            energy_wh=energy_wh,
            power_w=power_w,
            current_a=current_a,
            voltage_v=voltage,
        ),
        raw=data,
    )
