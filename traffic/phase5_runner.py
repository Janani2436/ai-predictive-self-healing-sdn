"""
traffic/phase5_runner.py

LINUX-SIMULATION-REQUIRED

Phase 5 traffic-generation runner.

This runner:
1. Builds the existing redundant campus topology.
2. Uses the existing topology lifecycle to start Mininet.
3. Allows controller/RSTP convergence before testing connectivity.
4. Verifies basic host connectivity.
5. Runs normal traffic.
6. Runs simultaneous high-rate competing traffic.
7. Saves the real iperf3 results.
8. Stops the Mininet network cleanly.

No traffic or performance results are fabricated.
"""

import argparse
import logging
import sys
import time

from topology.campus_topology import CampusTopology
from traffic.congestion_scenario import run_congestion_scenario
from traffic.normal_traffic import run_normal_traffic


logger = logging.getLogger(__name__)


def configure_logging() -> None:
    """
    Configure console logging for the Phase 5 runner.
    """
    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s %(levelname)s "
            "%(name)s: %(message)s"
        ),
    )


def verify_connectivity(network) -> bool:
    """
    Run one Mininet pingall test and return whether
    all host-to-host probes succeeded.
    """
    logger.info(
        "[PHASE5] Running connectivity test."
    )

    loss = network.pingAll()

    logger.info(
        "[PHASE5] Pingall packet loss: %.1f%%",
        loss,
    )

    return loss == 0.0


def wait_for_connectivity(
    network,
    attempts: int = 3,
    wait_seconds: int = 5,
) -> bool:
    """
    Allow controller/RSTP learning to settle and retry
    pingall when temporary startup packet loss occurs.

    The method records each actual pingall result and does
    not fabricate successful connectivity.
    """
    if attempts <= 0:
        raise ValueError(
            "attempts must be greater than zero"
        )

    if wait_seconds < 0:
        raise ValueError(
            "wait_seconds cannot be negative"
        )

    for attempt in range(1, attempts + 1):
        logger.info(
            "[PHASE5] Connectivity attempt %d/%d.",
            attempt,
            attempts,
        )

        if verify_connectivity(network):
            logger.info(
                "[PHASE5] Connectivity established."
            )
            return True

        if attempt < attempts:
            logger.info(
                "[PHASE5] Temporary packet loss detected. "
                "Waiting %d seconds before retry.",
                wait_seconds,
            )
            time.sleep(wait_seconds)

    logger.error(
        "[PHASE5] Connectivity did not reach 0%% packet loss "
        "after %d attempts.",
        attempts,
    )

    return False


def run_phase5(
    controller_ip: str = "127.0.0.1",
    controller_port: int = 6653,
    duration_seconds: int = 10,
    normal_rate_mbps: float = 5.0,
    congestion_rate_mbps: float = 80.0,
) -> int:
    """
    Execute the complete Phase 5 traffic-generation experiment.
    """
    topology = CampusTopology(
        controller_ip=controller_ip,
        controller_port=controller_port,
    )

    network_started = False

    try:
        logger.info(
            "[PHASE5] Building and starting campus topology."
        )

        # CampusTopology.build() already starts the network.
        topology.build()

        network_started = True
        network = topology.net

        logger.info(
            "[PHASE5] Campus topology is running."
        )

        # --------------------------------------------------
        # Initial connectivity
        # --------------------------------------------------

        logger.info(
            "[PHASE5] Waiting for controller and RSTP "
            "convergence."
        )

        if not wait_for_connectivity(
            network=network,
            attempts=3,
            wait_seconds=5,
        ):
            logger.error(
                "[PHASE5] Initial connectivity validation failed."
            )
            return 1

        logger.info(
            "[PHASE5] Initial connectivity validation passed."
        )

        # --------------------------------------------------
        # Normal traffic
        # --------------------------------------------------

        logger.info(
            "[PHASE5] Starting normal traffic scenario."
        )

        normal_results = run_normal_traffic(
            network=network,
            duration_seconds=duration_seconds,
            rate_mbps=normal_rate_mbps,
        )

        logger.info(
            "[PHASE5] Normal traffic completed: %d flows.",
            len(normal_results),
        )

        # --------------------------------------------------
        # Connectivity before congestion
        # --------------------------------------------------

        logger.info(
            "[PHASE5] Re-checking connectivity before "
            "congestion scenario."
        )

        if not wait_for_connectivity(
            network=network,
            attempts=3,
            wait_seconds=3,
        ):
            logger.error(
                "[PHASE5] Connectivity failed before "
                "congestion scenario."
            )
            return 1

        logger.info(
            "[PHASE5] Connectivity confirmed before "
            "congestion scenario."
        )

        # --------------------------------------------------
        # Simultaneous congestion traffic
        # --------------------------------------------------

        logger.info(
            "[PHASE5] Starting simultaneous high-rate "
            "traffic scenario."
        )

        congestion_results = run_congestion_scenario(
            network=network,
            duration_seconds=duration_seconds,
            rate_mbps=congestion_rate_mbps,
        )

        logger.info(
            "[PHASE5] Congestion scenario completed: "
            "%d flows.",
            len(congestion_results),
        )

        # --------------------------------------------------
        # Final connectivity
        # --------------------------------------------------

        logger.info(
            "[PHASE5] Running final connectivity test."
        )

        final_connectivity = verify_connectivity(
            network
        )

        if final_connectivity:
            logger.info(
                "[PHASE5] Final connectivity test passed."
            )
        else:
            logger.warning(
                "[PHASE5] Final pingall reported packet loss."
            )

        logger.info(
            "[PHASE5] Phase 5 traffic experiment completed."
        )

        return 0

    except Exception:
        logger.exception(
            "[PHASE5] Phase 5 experiment failed."
        )
        return 1

    finally:
        if network_started:
            logger.info(
                "[PHASE5] Stopping network."
            )

            try:
                topology.stop()
            except Exception:
                logger.exception(
                    "[PHASE5] Error while stopping topology."
                )


def parse_arguments() -> argparse.Namespace:
    """
    Parse Phase 5 command-line arguments.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Run Phase 5 traffic-generation experiments "
            "on the smart-campus Mininet topology."
        )
    )

    parser.add_argument(
        "--controller-ip",
        default="127.0.0.1",
        help="Ryu controller IP address.",
    )

    parser.add_argument(
        "--controller-port",
        type=int,
        default=6653,
        help="Ryu OpenFlow controller port.",
    )

    parser.add_argument(
        "--duration",
        type=int,
        default=10,
        help="Traffic duration in seconds.",
    )

    parser.add_argument(
        "--normal-rate",
        type=float,
        default=5.0,
        help="Normal UDP traffic rate in Mbps.",
    )

    parser.add_argument(
        "--congestion-rate",
        type=float,
        default=80.0,
        help="High-rate UDP traffic per competing flow.",
    )

    return parser.parse_args()


def main() -> int:
    """
    Main entry point.
    """
    configure_logging()

    args = parse_arguments()

    if args.duration <= 0:
        print(
            "Error: duration must be greater than zero.",
            file=sys.stderr,
        )
        return 1

    if args.normal_rate <= 0:
        print(
            "Error: normal-rate must be greater than zero.",
            file=sys.stderr,
        )
        return 1

    if args.congestion_rate <= 0:
        print(
            "Error: congestion-rate must be greater than zero.",
            file=sys.stderr,
        )
        return 1

    return run_phase5(
        controller_ip=args.controller_ip,
        controller_port=args.controller_port,
        duration_seconds=args.duration,
        normal_rate_mbps=args.normal_rate,
        congestion_rate_mbps=args.congestion_rate,
    )


if __name__ == "__main__":
    raise SystemExit(main())
