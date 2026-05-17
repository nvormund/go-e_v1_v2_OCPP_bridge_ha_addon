from __future__ import annotations

import asyncio
import base64
import logging
from datetime import timezone
from typing import Any

import websockets
from ocpp.routing import on
from ocpp.v16 import ChargePoint as OcppChargePoint
from ocpp.v16 import call, call_result
from ocpp.v16.enums import RegistrationStatus, Reason

from .config import AppConfig
from .goe_client import GoeClient
from .models import ChargerSnapshot
from .safety import may_remote_start, may_remote_stop
from .state import BridgeState, StateStore

LOGGER = logging.getLogger(__name__)


class GoeOcppChargePoint(OcppChargePoint):
    def __init__(self, config: AppConfig, connection: Any, goe_client: GoeClient, state_store: StateStore):
        super().__init__(config.ocpp.charge_point_id, connection)
        self.config = config
        self.goe_client = goe_client
        self.state_store = state_store
        self.state = state_store.load()
        self.heartbeat_interval_seconds = config.bridge.heartbeat_interval_seconds

    async def boot(self) -> None:
        while True:
            request = call.BootNotificationPayload(
                charge_point_model="go-eCharger",
                charge_point_vendor="go-e",
                firmware_version="unknown",
            )
            response = await self.call(request)
            LOGGER.info("BootNotification response: %s", response)

            if response.interval:
                self.heartbeat_interval_seconds = response.interval
                LOGGER.info("Using backend heartbeat interval: %s seconds", response.interval)

            status = _enum_value(response.status)
            if status == RegistrationStatus.accepted.value:
                return

            if status == RegistrationStatus.pending.value:
                retry_seconds = response.interval or self.config.bridge.reconnect_interval_seconds
                LOGGER.warning("BootNotification is pending. Retrying in %.1f seconds", retry_seconds)
                await asyncio.sleep(retry_seconds)
                continue

            raise RuntimeError(f"BootNotification was rejected by backend: {status}")

    async def send_heartbeat(self) -> None:
        response = await self.call(call.HeartbeatPayload())
        LOGGER.debug("Heartbeat response: %s", response)

    async def send_status(self, snapshot: ChargerSnapshot) -> None:
        await self.call(
            call.StatusNotificationPayload(
                connector_id=0,
                error_code="NoError",
                status="Available",
            )
        )
        await self.call(
            call.StatusNotificationPayload(
                connector_id=self.config.ocpp.connector_id,
                error_code="NoError",
                status=snapshot.status.value,
            )
        )
        self.state.last_status = snapshot.status.value
        self.state_store.save(self.state)

    async def send_meter_values(self, snapshot: ChargerSnapshot) -> None:
        sampled_values = []
        meter = snapshot.meter
        effective_energy_wh = self._effective_meter_wh(snapshot)
        if effective_energy_wh is not None:
            sampled_values.append(
                {
                    "value": str(round(effective_energy_wh, 3)),
                    "context": "Sample.Periodic",
                    "format": "Raw",
                    "measurand": "Energy.Active.Import.Register",
                    "unit": "Wh",
                }
            )
            self.state.last_meter_wh = effective_energy_wh
        if meter.power_w is not None:
            sampled_values.append(
                {
                    "value": str(round(meter.power_w, 3)),
                    "context": "Sample.Periodic",
                    "format": "Raw",
                    "measurand": "Power.Active.Import",
                    "unit": "W",
                }
            )
        if meter.current_a is not None:
            sampled_values.append(
                {
                    "value": str(round(meter.current_a, 3)),
                    "context": "Sample.Periodic",
                    "format": "Raw",
                    "measurand": "Current.Import",
                    "unit": "A",
                }
            )
        if meter.voltage_v is not None:
            sampled_values.append(
                {
                    "value": str(round(meter.voltage_v, 3)),
                    "context": "Sample.Periodic",
                    "format": "Raw",
                    "measurand": "Voltage",
                    "unit": "V",
                }
            )
        if not sampled_values:
            LOGGER.debug("No meter values available in go-e snapshot")
            return

        timestamp = meter.timestamp.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        await self.call(
            call.MeterValuesPayload(
                connector_id=self.config.ocpp.connector_id,
                meter_value=[{"timestamp": timestamp, "sampledValue": sampled_values}],
                transaction_id=self.state.active_transaction_id,
            )
        )
        self.state_store.save(self.state)

    async def start_transaction(self, id_tag: str) -> None:
        snapshot = await self.goe_client.get_snapshot()
        meter_start = _meter_wh_as_int(snapshot.meter.energy_wh, self.state.last_meter_wh)
        timestamp = _timestamp(snapshot)

        response = await self.call(
            call.StartTransactionPayload(
                connector_id=self.config.ocpp.connector_id,
                id_tag=id_tag,
                meter_start=meter_start,
                timestamp=timestamp,
            )
        )

        self.state.active_transaction_id = response.transaction_id
        self.state.active_id_tag = id_tag
        self.state.transaction_start_meter_wh = float(meter_start)
        self.state.transaction_start_session_wh = snapshot.meter.session_energy_wh
        self.state.last_meter_wh = snapshot.meter.energy_wh
        self.state_store.save(self.state)
        LOGGER.info("StartTransaction accepted with transactionId=%s", response.transaction_id)

    async def stop_transaction(
        self,
        transaction_id: int | None = None,
        reason: Reason = Reason.remote,
        snapshot: ChargerSnapshot | None = None,
    ) -> None:
        snapshot = snapshot or await self.goe_client.get_snapshot()
        meter_stop = _meter_wh_as_int(self._effective_meter_wh(snapshot), snapshot.meter.energy_wh, self.state.last_meter_wh)
        ocpp_transaction_id = transaction_id or self.state.active_transaction_id
        if ocpp_transaction_id is None:
            LOGGER.warning("StopTransaction skipped because no transaction id is known")
            return

        response = await self.call(
            call.StopTransactionPayload(
                transaction_id=ocpp_transaction_id,
                meter_stop=meter_stop,
                timestamp=_timestamp(snapshot),
                reason=reason,
                id_tag=self.state.active_id_tag,
            )
        )

        LOGGER.info("StopTransaction response for transactionId=%s: %s", ocpp_transaction_id, response)
        self.state.active_transaction_id = None
        self.state.active_id_tag = None
        self.state.transaction_start_meter_wh = None
        self.state.transaction_start_session_wh = None
        self.state.last_meter_wh = snapshot.meter.energy_wh
        self.state_store.save(self.state)

    @on("RemoteStartTransaction")
    async def on_remote_start_transaction(self, id_tag: str, **kwargs: Any) -> call_result.RemoteStartTransactionPayload:
        decision = may_remote_start(self.config.bridge)
        if not decision.allowed:
            LOGGER.warning("RemoteStartTransaction rejected: %s; idTag=%s", decision.reason, id_tag)
            return call_result.RemoteStartTransactionPayload(status="Rejected")

        LOGGER.info("RemoteStartTransaction accepted for idTag=%s kwargs=%s", id_tag, kwargs)
        asyncio.create_task(self._handle_remote_start(id_tag), name="remote-start-transaction")
        return call_result.RemoteStartTransactionPayload(status="Accepted")

    @on("RemoteStopTransaction")
    async def on_remote_stop_transaction(self, transaction_id: int, **kwargs: Any) -> call_result.RemoteStopTransactionPayload:
        decision = may_remote_stop(self.config.bridge)
        if not decision.allowed:
            LOGGER.warning("RemoteStopTransaction rejected: %s; transactionId=%s", decision.reason, transaction_id)
            return call_result.RemoteStopTransactionPayload(status="Rejected")

        LOGGER.info("RemoteStopTransaction accepted for transactionId=%s kwargs=%s", transaction_id, kwargs)
        asyncio.create_task(self._handle_remote_stop(transaction_id), name="remote-stop-transaction")
        return call_result.RemoteStopTransactionPayload(status="Accepted")

    async def _handle_remote_start(self, id_tag: str) -> None:
        try:
            await self.goe_client.start_charging()
            await self.start_transaction(id_tag)
        except Exception:
            LOGGER.exception("Failed to execute RemoteStartTransaction workflow")

    async def _handle_remote_stop(self, transaction_id: int) -> None:
        try:
            snapshot = await self.goe_client.get_snapshot()
            await self.goe_client.stop_charging()
            await self.stop_transaction(transaction_id, Reason.remote, snapshot)
        except Exception:
            LOGGER.exception("Failed to execute RemoteStopTransaction workflow")

    def _effective_meter_wh(self, snapshot: ChargerSnapshot) -> float | None:
        meter = snapshot.meter
        if (
            self.state.active_transaction_id is not None
            and self.state.transaction_start_meter_wh is not None
            and self.state.transaction_start_session_wh is not None
            and meter.session_energy_wh is not None
        ):
            session_delta = max(0.0, meter.session_energy_wh - self.state.transaction_start_session_wh)
            return self.state.transaction_start_meter_wh + session_delta
        return meter.energy_wh


async def run_bridge(config: AppConfig, goe_client: GoeClient, state_store: StateStore) -> None:
    try:
        LOGGER.info("Connecting to OCPP backend: %s", config.ocpp.backend_url)
        async with _connect_websocket(config) as websocket:
            charge_point = GoeOcppChargePoint(config, websocket, goe_client, state_store)
            receive_task = asyncio.create_task(charge_point.start(), name="ocpp-receive")
            await charge_point.boot()
            await charge_point.send_heartbeat()
            periodic_task = asyncio.create_task(_run_periodic_tasks(charge_point), name="periodic-tasks")
            done, pending = await asyncio.wait(
                {receive_task, periodic_task},
                return_when=asyncio.FIRST_EXCEPTION,
            )
            for task in pending:
                task.cancel()
            for task in done:
                task.result()
    finally:
        LOGGER.info("Closing go-e client after OCPP session ended")
        await goe_client.close()


def _connect_websocket(config: AppConfig):
    headers = _auth_headers(config)
    connect_kwargs = {
        "subprotocols": ["ocpp1.6"],
        "ping_interval": config.bridge.websocket_ping_interval_seconds,
        "ping_timeout": config.bridge.websocket_ping_timeout_seconds,
    }
    if headers:
        connect_kwargs["extra_headers"] = headers
    try:
        return websockets.connect(config.ocpp.backend_url, **connect_kwargs)
    except TypeError:
        if headers:
            connect_kwargs.pop("extra_headers", None)
            connect_kwargs["additional_headers"] = headers
        return websockets.connect(config.ocpp.backend_url, **connect_kwargs)


async def _run_periodic_tasks(charge_point: GoeOcppChargePoint) -> None:
    heartbeat_task = asyncio.create_task(_heartbeat_loop(charge_point), name="heartbeat-loop")
    meter_task = asyncio.create_task(_meter_loop(charge_point), name="meter-loop")
    await asyncio.gather(heartbeat_task, meter_task)


async def _heartbeat_loop(charge_point: GoeOcppChargePoint) -> None:
    while True:
        await asyncio.sleep(charge_point.heartbeat_interval_seconds)
        await charge_point.send_heartbeat()


async def _meter_loop(charge_point: GoeOcppChargePoint) -> None:
    while True:
        try:
            snapshot = await charge_point.goe_client.get_snapshot()
            await charge_point.send_status(snapshot)
            await charge_point.send_meter_values(snapshot)
        except Exception:
            LOGGER.exception("Failed to poll go-e charger or send OCPP telemetry")
        await asyncio.sleep(charge_point.config.bridge.meter_interval_seconds)


def _auth_headers(config: AppConfig) -> dict[str, str]:
    user = config.ocpp.basic_auth_user
    password = config.ocpp.basic_auth_password
    if not user:
        return {}
    token = base64.b64encode(f"{user}:{password}".encode("utf-8")).decode("ascii")
    return {"Authorization": f"Basic {token}"}


def _timestamp(snapshot: ChargerSnapshot) -> str:
    return snapshot.meter.timestamp.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _meter_wh_as_int(*values: float | None) -> int:
    for value in values:
        if value is not None:
            return int(round(value))
    return 0


def _enum_value(value: Any) -> Any:
    return getattr(value, "value", value)
