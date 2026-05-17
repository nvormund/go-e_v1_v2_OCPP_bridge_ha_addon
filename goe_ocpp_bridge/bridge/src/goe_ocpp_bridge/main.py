from __future__ import annotations

import argparse
import asyncio
import logging
from pathlib import Path

from .config import AppConfig, load_config
from .goe_client import GoeClient
from .goe_v1 import GoeV1Client
from .goe_v2 import GoeV2Client
from .logging_setup import setup_logging
from .ocpp_bridge import run_bridge
from .state import StateStore

LOGGER = logging.getLogger(__name__)


async def async_main() -> None:
    parser = argparse.ArgumentParser(description="go-eCharger to OCPP 1.6 bridge")
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    args = parser.parse_args()

    config = load_config(args.config)
    log_file = _resolve_optional_path(config, config.bridge.log_file)
    setup_logging(config.bridge.log_level, log_file)

    LOGGER.info("Starting go-e OCPP bridge")
    LOGGER.info("Home Assistant integration is intentionally not used or modified")
    LOGGER.info(
        "Modes: dry_run=%s read_only=%s allow_remote_start=%s allow_remote_stop=%s",
        config.bridge.dry_run,
        config.bridge.read_only,
        config.bridge.allow_remote_start,
        config.bridge.allow_remote_stop,
    )

    state_path = _resolve_path(config, config.bridge.state_file)
    state_store = StateStore(state_path)

    while True:
        goe_client = await create_goe_client(config)
        try:
            await run_bridge(config, goe_client, state_store)
            LOGGER.warning(
                "OCPP connection ended. Reconnecting in %.1f seconds",
                config.bridge.reconnect_interval_seconds,
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            LOGGER.exception(
                "OCPP bridge crashed or disconnected. Reconnecting in %.1f seconds",
                config.bridge.reconnect_interval_seconds,
            )
        await asyncio.sleep(config.bridge.reconnect_interval_seconds)


async def create_goe_client(config: AppConfig) -> GoeClient:
    if config.goe.api_version == "v1":
        return GoeV1Client(config.goe)
    if config.goe.api_version == "v2":
        return GoeV2Client(config.goe)

    v2 = GoeV2Client(config.goe)
    try:
        await v2.get_snapshot()
        LOGGER.info("Detected go-e API v2")
        return v2
    except Exception:
        await v2.close()
        LOGGER.info("go-e API v2 probe failed, falling back to v1")
        return GoeV1Client(config.goe)


def _resolve_path(config: AppConfig, path_value: str) -> Path:
    path = Path(path_value).expanduser()
    if path.is_absolute():
        return path
    return config.base_dir / path


def _resolve_optional_path(config: AppConfig, path_value: str) -> Path | None:
    if not path_value:
        return None
    return _resolve_path(config, path_value)


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
