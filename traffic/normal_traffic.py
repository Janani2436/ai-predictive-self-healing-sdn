"""
traffic/normal_traffic.py

LINUX-SIMULATION-REQUIRED

Normal campus traffic scenario.

Traffic is intentionally moderate and is used to establish normal
network traffic conditions before congestion experiments.
"""

import argparse
import logging

from traffic.traffic_generator import (
    run_iperf_client,
    save_traffic_result,
    start_iperf_server,
    stop_iperf_server,
    wait_for_server,
)

logger = logging.getLogger(__name__)


def run_normal_traffic(
    network,
    duration_seconds: int = 10,
    rate_mbps: float = 5.0,
) -> list[dict]:
    """
    Generate moderate UDP traffic between two host pairs.

    Host pairs:
        h1 -> h2
        h3 -> h4
    """
    h1 = network.get("h1")
    h2 = network.get("h2")
    h3 = network.get("h3")
    h4 = network.get("h4")

    servers = [
        start_iperf_server(h2),
        start_iperf_server(h4),
    ]

    try:
        wait_for_server()

        results = [
            run_iperf_client(
                h1,
                h2.IP(),
                duration_seconds=duration_seconds,
                rate_mbps=rate_mbps,
            ),
            run_iperf_client(
                h3,
                h4.IP(),
                duration_seconds=duration_seconds,
                rate_mbps=rate_mbps,
            ),
        ]

        for result in results:
            save_traffic_result(result, filename="normal_traffic.jsonl")

        return results

    finally:
        for server in servers:
            stop_iperf_server(server)


def main() -> None:
    """
    Standalone execution is intentionally not implemented here.

    The scenario requires the Phase 4 CampusTopology Mininet network.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", type=int, default=10)
    parser.add_argument("--rate", type=float, default=5.0)
    args = parser.parse_args()

    print(
        "normal_traffic.py is a scenario module and must be invoked "
        "with an active CampusTopology Mininet network."
    )
    print(f"Configured duration: {args.duration}s")
    print(f"Configured rate: {args.rate} Mbps")


if __name__ == "__main__":
    main()
