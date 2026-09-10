"""
traffic/traffic_generator.py

LINUX-SIMULATION-REQUIRED

Utilities for generating and recording iperf3 traffic
inside the Mininet smart-campus simulation.
"""

import json
import logging
import os
import subprocess
import time
from datetime import datetime
from typing import Any


logger = logging.getLogger(__name__)


def start_iperf_server(
    host: Any,
    port: int = 5201,
) -> Any:
    """
    Start an iperf3 UDP/TCP server on a Mininet host.
    """
    if port <= 0:
        raise ValueError("port must be greater than zero")

    logger.info(
        "[TRAFFIC] Starting iperf3 server on %s:%d",
        host.name,
        port,
    )

    return host.popen(
        [
            "iperf3",
            "-s",
            "-p",
            str(port),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def stop_iperf_server(
    process: Any,
) -> None:
    """
    Stop an iperf3 server process cleanly.
    """
    if process is None:
        return

    try:
        process.terminate()
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
    except Exception as exc:
        logger.warning(
            "[TRAFFIC] Error while stopping iperf3 server: %s",
            exc,
        )


def start_iperf_client(
    source: Any,
    destination_ip: str,
    duration_seconds: int = 10,
    rate_mbps: float | None = None,
    port: int = 5201,
) -> Any:
    """
    Start an iperf3 client asynchronously from a Mininet host.

    The returned process can be started alongside other clients so that
    multiple traffic flows can run simultaneously.
    """
    if duration_seconds <= 0:
        raise ValueError(
            "duration_seconds must be greater than zero"
        )

    if rate_mbps is not None and rate_mbps <= 0:
        raise ValueError(
            "rate_mbps must be greater than zero"
        )

    command = [
        "iperf3",
        "-c",
        destination_ip,
        "-p",
        str(port),
        "-t",
        str(duration_seconds),
        "-J",
    ]

    protocol = "tcp"

    if rate_mbps is not None:
        command.extend(
            [
                "-u",
                "-b",
                f"{rate_mbps}M",
            ]
        )
        protocol = "udp"

    logger.info(
        "[TRAFFIC] Starting async client: %s -> %s | "
        "protocol=%s | rate=%s Mbps | duration=%s seconds",
        source.name,
        destination_ip,
        protocol,
        rate_mbps if rate_mbps is not None else "TCP",
        duration_seconds,
    )

    return source.popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def run_iperf_client(
    source: Any,
    destination_ip: str,
    duration_seconds: int = 10,
    rate_mbps: float | None = None,
    port: int = 5201,
) -> dict:
    """
    Run an iperf3 client synchronously and return the result.

    UDP is used when rate_mbps is specified.
    TCP is used when rate_mbps is None.
    """
    process = start_iperf_client(
        source=source,
        destination_ip=destination_ip,
        duration_seconds=duration_seconds,
        rate_mbps=rate_mbps,
        port=port,
    )

    output, _ = process.communicate()

    protocol = "udp" if rate_mbps is not None else "tcp"

    result = {
        "timestamp": datetime.now().isoformat(),
        "source": source.name,
        "destination_ip": destination_ip,
        "protocol": protocol,
        "duration_seconds": duration_seconds,
        "rate_mbps": rate_mbps,
        "raw_output": output,
    }

    try:
        result["iperf3"] = json.loads(output)
    except json.JSONDecodeError:
        result["iperf3"] = None

        logger.warning(
            "[TRAFFIC] Could not parse iperf3 JSON output "
            "from %s",
            source.name,
        )

    return result


def save_traffic_result(
    result: dict,
    output_dir: str = "logs/traffic",
    filename: str = "traffic_results.jsonl",
) -> str:
    """
    Save one traffic result as a JSON Lines record.
    """
    os.makedirs(output_dir, exist_ok=True)

    output_path = os.path.join(
        output_dir,
        filename,
    )

    with open(
        output_path,
        "a",
        encoding="utf-8",
    ) as file:
        file.write(
            json.dumps(
                result,
                default=str,
            )
            + "\n"
        )

    logger.info(
        "[TRAFFIC] Traffic result saved to %s",
        output_path,
    )

    return output_path


def wait_for_server(
    seconds: float = 1.0,
) -> None:
    """
    Wait briefly for iperf3 servers to become ready.
    """
    if seconds < 0:
        raise ValueError(
            "seconds cannot be negative"
        )

    time.sleep(seconds)
