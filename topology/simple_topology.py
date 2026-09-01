"""
topology/simple_topology.py
LINUX-SIMULATION-REQUIRED

Minimal Mininet topology for initial SDN verification:

    H1 --- S1 --- H2

Purpose:
    - Verify Mininet + OVS + Ryu + OpenFlow 1.3 are working end-to-end.
    - Confirm host-to-host connectivity via pingall.
    - Establish the baseline before building the full campus topology.

This file CANNOT be executed on the Windows development machine.
It requires:
    - Mininet  (sudo apt-get install mininet)
    - Open vSwitch  (sudo apt-get install openvswitch-switch)
    - Ryu SDN Controller  (pip install ryu)
    - Linux kernel networking (network namespaces, OVS kernel module)

Run on the personal Ubuntu/WSL2 simulation machine with:
    sudo python topology/simple_topology.py [--controller-ip 127.0.0.1] [--controller-port 6633]

Status: LINUX-SIMULATION-REQUIRED — not yet executed.
"""

# LINUX-SIMULATION-REQUIRED
# This module requires Mininet and Open vSwitch running on Ubuntu.
# It cannot be executed on the Windows development machine.

import argparse
import logging
import sys

from topology.topology_utils import (
    configure_ovs_openflow13,
    get_controller_config,
    load_config,
    make_link_params,
    verify_openflow_version,
    format_host_ip,
    DEFAULT_CONTROLLER_IP,
    DEFAULT_CONTROLLER_PORT,
    DEFAULT_LINK_BW_MBPS,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Topology definition
# ---------------------------------------------------------------------------

class SimpleTopology:
    """
    Minimal h1-s1-h2 Mininet topology for initial SDN verification.

    Topology:
        H1 (10.0.0.1) --- S1 [OVS, OF1.3] --- H2 (10.0.0.2)

    The switch connects to the Ryu controller via OpenFlow 1.3 on the
    configured IP and port.
    """

    def __init__(
        self,
        controller_ip: str = DEFAULT_CONTROLLER_IP,
        controller_port: int = DEFAULT_CONTROLLER_PORT,
        link_bw_mbps: int = DEFAULT_LINK_BW_MBPS,
        link_delay_ms: str = "1ms",
    ) -> None:
        """
        Initialise topology parameters.

        Args:
            controller_ip:   IP address of the Ryu controller.
            controller_port: TCP port of the Ryu controller.
            link_bw_mbps:    Bandwidth for all links in Mbps.
            link_delay_ms:   Propagation delay for all links (e.g., "1ms").
        """
        self.controller_ip = controller_ip
        self.controller_port = controller_port
        self.link_bw_mbps = link_bw_mbps
        self.link_delay_ms = link_delay_ms
        self.net = None  # Mininet network object (set in build())

    def build(self) -> None:
        """
        Build and start the Mininet network.

        Creates h1, h2, s1, links them, configures OpenFlow 1.3,
        and starts the network.

        Raises:
            ImportError: If Mininet is not installed (Linux required).
            RuntimeError: If network creation or OVS configuration fails.
        """
        # Import Mininet here so that importing this module on Windows
        # does not immediately raise ImportError — it only fails when
        # build() is actually called.
        try:
            from mininet.net import Mininet
            from mininet.node import OVSSwitch, RemoteController
            from mininet.link import TCLink
            from mininet.log import setLogLevel
        except ImportError as exc:
            raise ImportError(
                "Mininet is not installed. "
                "This topology requires Ubuntu/WSL2 with Mininet installed. "
                "Run: sudo apt-get install mininet"
            ) from exc

        setLogLevel("info")

        logger.info("[TOPOLOGY] Building simple topology: H1 --- S1 --- H2")
        logger.info(
            "[TOPOLOGY] Controller: %s:%d", self.controller_ip, self.controller_port
        )

        # Create remote controller reference (Ryu running separately)
        controller = RemoteController(
            "c0",
            ip=self.controller_ip,
            port=self.controller_port,
        )

        # Instantiate network with OVS switches and TC links (for BW/delay control)
        self.net = Mininet(
            controller=controller,
            switch=OVSSwitch,
            link=TCLink,
            autoSetMacs=True,
        )

        # Add controller
        self.net.addController(controller)
        logger.info("[TOPOLOGY] Remote controller added: %s:%d",
                    self.controller_ip, self.controller_port)

        # Add switch
        s1 = self.net.addSwitch("s1", cls=OVSSwitch, protocols=OPENFLOW_13_PROTOCOL)
        logger.info("[TOPOLOGY] Switch s1 added")

        # Add hosts with explicit IPs
        h1 = self.net.addHost("h1", ip=format_host_ip(1))
        h2 = self.net.addHost("h2", ip=format_host_ip(2))
        logger.info("[TOPOLOGY] Hosts added: h1=%s  h2=%s",
                    format_host_ip(1), format_host_ip(2))

        # Add links with configurable parameters
        link_params = make_link_params(
            bw_mbps=self.link_bw_mbps,
            delay_ms=self.link_delay_ms,
        )
        self.net.addLink(h1, s1, **link_params)
        self.net.addLink(s1, h2, **link_params)
        logger.info(
            "[TOPOLOGY] Links added: H1-S1-H2  bw=%dMbps  delay=%s",
            self.link_bw_mbps, self.link_delay_ms,
        )

        # Start network
        logger.info("[TOPOLOGY] Starting network...")
        self.net.start()
        logger.info("[TOPOLOGY] Network started.")

        # Configure switch for OpenFlow 1.3 (belt-and-suspenders after start)
        configure_ovs_openflow13(s1)
        if not verify_openflow_version(s1):
            logger.warning(
                "[TOPOLOGY] OpenFlow 1.3 could not be confirmed on s1 — "
                "check controller connection."
            )

        logger.info("[TOPOLOGY] Simple topology ready.")

    def run_pingall(self) -> float:
        """
        Run Mininet's built-in pingAll test and return the drop percentage.

        Returns:
            Packet drop percentage (0.0 = full connectivity).

        Raises:
            RuntimeError: If the network has not been built yet.
        """
        if self.net is None:
            raise RuntimeError("Network not built. Call build() first.")
        logger.info("[TOPOLOGY] Running pingAll connectivity test...")
        drop_pct = self.net.pingAll()
        if drop_pct == 0.0:
            logger.info("[TOPOLOGY] pingAll PASSED — 0%% packet drop.")
        else:
            logger.warning(
                "[TOPOLOGY] pingAll FAILED — %.1f%% packet drop.", drop_pct
            )
        return drop_pct

    def run_cli(self) -> None:
        """
        Drop into the interactive Mininet CLI for manual inspection.

        Raises:
            RuntimeError: If the network has not been built yet.
        """
        if self.net is None:
            raise RuntimeError("Network not built. Call build() first.")
        from mininet.cli import CLI
        logger.info("[TOPOLOGY] Entering Mininet CLI. Type 'exit' to quit.")
        CLI(self.net)

    def stop(self) -> None:
        """
        Stop the Mininet network and clean up resources.
        """
        if self.net is not None:
            logger.info("[TOPOLOGY] Stopping network...")
            self.net.stop()
            self.net = None
            logger.info("[TOPOLOGY] Network stopped.")
        else:
            logger.debug("[TOPOLOGY] stop() called but network was not running.")


# Module-level constant used inside build() — defined after imports so
# the module can be imported on Windows without Mininet present.
OPENFLOW_13_PROTOCOL = "OpenFlow13"


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the topology script."""
    parser = argparse.ArgumentParser(
        description="Simple h1-s1-h2 Mininet topology with OpenFlow 1.3",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--controller-ip",
        default=None,
        help="Ryu controller IP address (overrides config.yaml)",
    )
    parser.add_argument(
        "--controller-port",
        type=int,
        default=None,
        help="Ryu controller TCP port (overrides config.yaml)",
    )
    parser.add_argument(
        "--bw",
        type=int,
        default=DEFAULT_LINK_BW_MBPS,
        help="Link bandwidth in Mbps",
    )
    parser.add_argument(
        "--delay",
        default="1ms",
        help="Link propagation delay (e.g., '2ms')",
    )
    parser.add_argument(
        "--pingall",
        action="store_true",
        help="Run pingAll test immediately after startup and exit",
    )
    parser.add_argument(
        "--no-cli",
        action="store_true",
        help="Do not open the interactive CLI (useful for scripted runs)",
    )
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to config.yaml (relative to repo root)",
    )
    return parser.parse_args()


def main() -> int:
    """
    Main entry point — build and run the simple topology.

    Returns:
        0 on success, 1 on failure.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    )

    args = _parse_args()

    # Load config, then apply any CLI overrides
    config = load_config(args.config)
    ctrl_ip, ctrl_port = get_controller_config(config)

    if args.controller_ip is not None:
        ctrl_ip = args.controller_ip
    if args.controller_port is not None:
        ctrl_port = args.controller_port

    topology = SimpleTopology(
        controller_ip=ctrl_ip,
        controller_port=ctrl_port,
        link_bw_mbps=args.bw,
        link_delay_ms=args.delay,
    )

    try:
        topology.build()

        if args.pingall:
            drop = topology.run_pingall()
            topology.stop()
            return 0 if drop == 0.0 else 1

        if not args.no_cli:
            topology.run_cli()

        return 0

    except ImportError as exc:
        logger.critical(
            "[TOPOLOGY] Cannot start topology: %s\n"
            "This script requires Mininet on Ubuntu/WSL2. "
            "It cannot run on Windows.",
            exc,
        )
        return 1
    except KeyboardInterrupt:
        logger.info("[TOPOLOGY] Interrupted by user.")
        return 0
    except Exception as exc:
        logger.critical("[TOPOLOGY] Unexpected error: %s", exc, exc_info=True)
        return 1
    finally:
        topology.stop()


if __name__ == "__main__":
    sys.exit(main())
