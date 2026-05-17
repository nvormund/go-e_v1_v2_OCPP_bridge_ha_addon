from __future__ import annotations

from dataclasses import dataclass

from .config import BridgeConfig


@dataclass(frozen=True)
class SafetyDecision:
    allowed: bool
    reason: str


def may_remote_start(config: BridgeConfig) -> SafetyDecision:
    if config.read_only:
        return SafetyDecision(False, "read_only is enabled")
    if config.dry_run:
        return SafetyDecision(False, "dry_run is enabled")
    if not config.allow_remote_start:
        return SafetyDecision(False, "allow_remote_start is false")
    return SafetyDecision(True, "remote start is allowed")


def may_remote_stop(config: BridgeConfig) -> SafetyDecision:
    if config.read_only:
        return SafetyDecision(False, "read_only is enabled")
    if config.dry_run:
        return SafetyDecision(False, "dry_run is enabled")
    if not config.allow_remote_stop:
        return SafetyDecision(False, "allow_remote_stop is false")
    return SafetyDecision(True, "remote stop is allowed")
