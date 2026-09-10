"""
traffic/congestion_scenario.py

LINUX-SIMULATION-REQUIRED

Controlled high-rate traffic scenario for the smart-campus topology.

This module generates simultaneous UDP flows that share the H4 access link.
It does not assume or fabricate congestion results.
"""

import json
import logging
from datetime import datetime
from typing import Any

from traffic.traffic_generator import (
    save_traffic_result,
    start_iperf_client,
    start_iperf_server,
    stop_iperf_server,
    wait_for_server,
)

logger = logging.getLogger(__name__)


def run_congestion_scenario(
    network: Any,
    duration_seconds: int = 10,
    rate_mbps: float = 80.0,
) -> list[dict]:
    """
    Generate simultaneous competing high-rate UDP flows.

    Host pairs:
        H1 → H4 : UDP : port 5201
        H2 → H4 : UDP : port 5202

    Both flows share the A4-H4 100 Mbps access link.

    Both clients are started before either client is collected.
    Therefore, the flows overlap in time.
    """
    if duration_seconds <= 0:
        raise ValueError("duration_seconds must be greater than zero")

    if rate_mbps <= 0:
        raise ValueError("rate_mbps must be greater than zero")

    h1 = network.get("h1")
    h2 = network.get("h2")
    h4 = network.get("h4")

    flows = [
        (h1, h4, 5201),
        (h2, h4, 5202),
    ]

    servers = [
        start_iperf_server(h4, port=5201),
        start_iperf_server(h4, port=5202),
    ]

    clients = []

    try:
        wait_for_server()

        # Start all clients before waiting for any result.
        for source, destination, port in flows:
            process = start_iperf_client(
                source,
                destination.IP(),
                duration_seconds=duration_seconds,
                rate_mbps=rate_mbps,
                port=port,
            )

            clients.append(
                {
                    "process": process,
                    "source": source.name,
                    "destination_ip": destination.IP(),
                    "port": port,
                }
            )

        results = []

        # Collect all completed client processes.
        for client in clients:
            output, _ = client["process"].communicate()

            record = {
                "timestamp": datetime.now().isoformat(),
                "source": client["source"],
                "destination_ip": client["destination_ip"],
                "protocol": "udp",
                "port": client["port"],
                "duration_seconds": duration_seconds,
                "rate_mbps": rate_mbps,
                "raw_output": output,
            }

            try:
                record["iperf3"] = json.loads(output)
            except json.JSONDecodeError:
                record["iperf3"] = None
                logger.warning(
                    "[TRAFFIC] Could not parse iperf3 JSON from %s",
                    client["source"],
                )

            results.append(record)

        for result in results:
            save_traffic_result(
                result,
                filename="congestion_traffic.jsonl",
            )

        logger.info(
            "[TRAFFIC] Simultaneous high-rate scenario completed: %d flows",
            len(results),
        )

        return results

    finally:
        for server in servers:
            stop_iperf_server(server)
