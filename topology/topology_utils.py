"""
topology/topology_utils.py
WINDOWS-COMPATIBLE (module structure, constants, config helpers)
LINUX-SIMULATION-REQUIRED (any function that calls the Mininet API)

Shared utility functions and constants for Mininet topology scripts.
Handles controller configuration, OVS switch setup, and link parameter
helpers used by both simple_topology.py and campus_topology.py.

All functions that interact with Mininet objects require the Ubuntu/WSL2
simulation machine. The config-loading helpers are safe on Windows.
"""

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# OpenFlow constants
# ---------------------------------------------------------------------------

OPENFLOW_13 = "OpenFlow13"          # OVS protocol string for OpenFlow 1.3
OPENFLOW_13_PORT = 6633              # Default controller TCP port
DEFAULT_CONTROLLER_IP = "127.0.0.1"
DEFAULT_CONTROLLER_PORT = 6633

# Default link parameters (can be overridden via config)
DEFAULT_LINK_BW_MBPS = 100          # Mbps
DEFAULT_LINK_DELAY_MS = "1ms"
DEFAULT_LINK_LOSS_PCT = 0           # percent
DEFAULT_LINK_MAX_QUEUE = 1000       # packets


# ---------------------------------------------------------------------------
# Configuration helpers (WINDOWS-COMPATIBLE)
# ---------------------------------------------------------------------------

def load_config(config_path: str = "config.yaml") -> dict[str, Any]:
    """
    Load project configuration from a YAML file.

    Falls back to sensible defaults if the file is not found, so that
    topology scripts can run without requiring a pre-existing config file.

    Args:
        config_path: Path to the YAML config file (relative to repo root).

    Returns:
        Dictionary of configuration values.
    """
    defaults: dict[str, Any] = {
        "controller": {
            "host": DEFAULT_CONTROLLER_IP,
            "port": DEFAULT_CONTROLLER_PORT,
            "openflow_version": 1.3,
        },
        "monitoring": {
            "poll_interval_seconds": 5,
            "link_capacity_mbps": DEFAULT_LINK_BW_MBPS,
        },
        "routing": {
            "congestion_threshold_pct": 80.0,
        },
    }

    # Resolve relative path from the repo root (two levels up from this file)
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    full_path = os.path.join(repo_root, config_path)

    if not os.path.exists(full_path):
        logger.warning(
            "Config file not found at %s — using defaults. "
            "Copy config.yaml.example to config.yaml to customise.",
            full_path,
        )
        return defaults

    try:
        import yaml  # PyYAML is a cross-platform dependency
        with open(full_path, "r", encoding="utf-8") as fh:
            loaded = yaml.safe_load(fh) or {}
        # Shallow-merge: loaded values override defaults
        for key, value in loaded.items():
            if isinstance(value, dict) and key in defaults:
                defaults[key].update(value)
            else:
                defaults[key] = value
        logger.info("Configuration loaded from %s", full_path)
        return defaults
    except Exception as exc:
        logger.error("Failed to load config from %s: %s — using defaults.", full_path, exc)
        return defaults


def get_controller_config(config: dict[str, Any]) -> tuple[str, int]:
    """
    Extract controller host and port from a config dictionary.

    Args:
        config: Configuration dictionary (from load_config).

    Returns:
        Tuple of (host: str, port: int).
    """
    host = config.get("controller", {}).get("host", DEFAULT_CONTROLLER_IP)
    port = config.get("controller", {}).get("port", DEFAULT_CONTROLLER_PORT)
    return str(host), int(port)


# ---------------------------------------------------------------------------
# OVS / switch helpers
# LINUX-SIMULATION-REQUIRED — these functions call Mininet/OVS APIs
# ---------------------------------------------------------------------------

def configure_ovs_openflow13(switch: Any) -> None:
    """
    Configure an OVS switch to use OpenFlow 1.3 exclusively.

    This function must be called after the Mininet network has started
    and the switch is connected to the controller.

    Args:
        switch: A Mininet OVSSwitch instance.

    Raises:
        RuntimeError: If the OVS configuration command fails.
    """
    # LINUX-SIMULATION-REQUIRED
    dpid = getattr(switch, "dpid", "unknown")
    logger.info("[TOPOLOGY] Configuring switch %s for OpenFlow 1.3", switch.name)
    try:
        result = switch.cmd(
            f"ovs-vsctl set bridge {switch.name} "
            f"protocols={OPENFLOW_13}"
        )
        if result.strip():
            logger.warning(
                "[TOPOLOGY] OVS config output for %s: %s", switch.name, result.strip()
            )
        logger.info(
            "[TOPOLOGY] Switch %s (dpid=%s) configured for OpenFlow 1.3", switch.name, dpid
        )
    except Exception as exc:
        raise RuntimeError(
            f"Failed to configure OpenFlow 1.3 on switch {switch.name}: {exc}"
        ) from exc


def set_switch_controller(switch: Any, controller_ip: str, controller_port: int) -> None:
    """
    Point an OVS switch at a specific Ryu controller.

    Args:
        switch: A Mininet OVSSwitch instance.
        controller_ip: Controller IP address.
        controller_port: Controller TCP port.

    Raises:
        RuntimeError: If the OVS command fails.
    """
    # LINUX-SIMULATION-REQUIRED
    logger.info(
        "[TOPOLOGY] Pointing switch %s at controller %s:%d",
        switch.name, controller_ip, controller_port,
    )
    try:
        result = switch.cmd(
            f"ovs-vsctl set-controller {switch.name} "
            f"tcp:{controller_ip}:{controller_port}"
        )
        if result.strip():
            logger.warning(
                "[TOPOLOGY] set-controller output for %s: %s", switch.name, result.strip()
            )
    except Exception as exc:
        raise RuntimeError(
            f"Failed to set controller on switch {switch.name}: {exc}"
        ) from exc


def verify_openflow_version(switch: Any) -> bool:
    """
    Check that an OVS switch is negotiating OpenFlow 1.3.

    Args:
        switch: A Mininet OVSSwitch instance.

    Returns:
        True if OpenFlow 1.3 is confirmed, False otherwise.
    """
    # LINUX-SIMULATION-REQUIRED
    try:
        result = switch.cmd(f"ovs-vsctl get bridge {switch.name} protocols")
        if OPENFLOW_13 in result:
            logger.info(
                "[TOPOLOGY] Switch %s: OpenFlow 1.3 confirmed (%s)",
                switch.name, result.strip(),
            )
            return True
        logger.warning(
            "[TOPOLOGY] Switch %s: unexpected protocol config: %s",
            switch.name, result.strip(),
        )
        return False
    except Exception as exc:
        logger.error(
            "[TOPOLOGY] Could not verify OpenFlow version on switch %s: %s",
            switch.name, exc,
        )
        return False


# ---------------------------------------------------------------------------
# Link parameter helpers (WINDOWS-COMPATIBLE — pure Python)
# ---------------------------------------------------------------------------

def make_link_params(
    bw_mbps: int = DEFAULT_LINK_BW_MBPS,
    delay_ms: str = DEFAULT_LINK_DELAY_MS,
    loss_pct: float = DEFAULT_LINK_LOSS_PCT,
    max_queue: int = DEFAULT_LINK_MAX_QUEUE,
) -> dict[str, Any]:
    """
    Build a link-parameters dictionary for Mininet TCLink.

    Args:
        bw_mbps:   Bandwidth in Mbps.
        delay_ms:  Propagation delay string (e.g., "2ms").
        loss_pct:  Packet loss percentage (0–100).
        max_queue: Maximum queue size in packets.

    Returns:
        Dictionary suitable for passing to Mininet addLink(..., **params).
    """
    return {
        "bw": bw_mbps,
        "delay": delay_ms,
        "loss": loss_pct,
        "max_queue_size": max_queue,
    }


def format_host_ip(host_number: int, subnet: str = "10.0.0") -> str:
    """
    Generate a host IP address from a subnet prefix and host number.

    Args:
        host_number: Integer suffix for the IP (e.g., 1 → 10.0.0.1).
        subnet:      Subnet prefix string without trailing dot.

    Returns:
        IP address string with /24 prefix.

    Raises:
        ValueError: If host_number is outside the valid range 1–254.
    """
    if not 1 <= host_number <= 254:
        raise ValueError(
            f"host_number must be between 1 and 254, got {host_number}"
        )
    return f"{subnet}.{host_number}/24"
