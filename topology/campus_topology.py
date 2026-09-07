"""
topology/campus_topology.py
LINUX-SIMULATION-REQUIRED

Redundant smart-campus Mininet topology for SDN routing and self-healing.

Topology:

    H1       H2
     |        |
    A1       A2
      \      /
       D1--D2
        \  /
         C1
        /  \
       A3   A4
       |     |
      H3    H4

Required redundant paths between H1 and H4:

    Path A: H1 -> A1 -> D1 -> C1 -> D2 -> A4 -> H4
    Path B: H1 -> A1 -> D1 -> D2 -> A4 -> H4

This topology is intended for the Linux/WSL2 simulation environment and
requires Mininet, Open vSwitch, and a running Ryu controller.

It cannot be executed on the Windows development machine.
"""

import argparse
import logging

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

OPENFLOW_13_PROTOCOL = "OpenFlow13"


class CampusTopology:
    """
    Redundant smart-campus topology.

    Switches:
        Core:         C1
        Distribution: D1, D2
        Access:       A1, A2, A3, A4

    Hosts:
        H1, H2, H3, H4

    Redundant H1-to-H4 paths:
        H1-A1-D1-C1-D2-A4-H4
        H1-A1-D1-D2-A4-H4
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
            controller_ip: IP address of the Ryu controller.
            controller_port: TCP port of the Ryu controller.
            link_bw_mbps: Bandwidth for topology links in Mbps.
            link_delay_ms: Propagation delay for topology links.
        """
        self.controller_ip = controller_ip
        self.controller_port = controller_port
        self.link_bw_mbps = link_bw_mbps
        self.link_delay_ms = link_delay_ms
        self.net = None

    def build(self) -> None:
        """
        Build and start the redundant campus Mininet network.

        Mininet is imported only when this method is called so that the
        module remains importable on Windows for structural testing.
        """
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

        logger.info("[TOPOLOGY] Building redundant smart-campus topology.")
        logger.info(
            "[TOPOLOGY] Controller: %s:%d",
            self.controller_ip,
            self.controller_port,
        )

        controller = RemoteController(
            "c0",
            ip=self.controller_ip,
            port=self.controller_port,
        )

        self.net = Mininet(
            controller=controller,
            switch=OVSSwitch,
            link=TCLink,
            autoSetMacs=True,
        )

        self.net.addController(controller)

        # Core layer.
        c1 = self.net.addSwitch(
            "c1",
            cls=OVSSwitch,
            dpid="0000000000000001",
            protocols=OPENFLOW_13_PROTOCOL,
        )

        # Distribution layer.
        d1 = self.net.addSwitch(
            "d1",
            cls=OVSSwitch,
            dpid="0000000000000002",
            protocols=OPENFLOW_13_PROTOCOL,
        )
        d2 = self.net.addSwitch(
            "d2",
            cls=OVSSwitch,
            dpid="0000000000000003",
            protocols=OPENFLOW_13_PROTOCOL,
        )

        # Access layer.
        a1 = self.net.addSwitch(
            "a1",
            cls=OVSSwitch,
            dpid="0000000000000004",
            protocols=OPENFLOW_13_PROTOCOL,
        )
        a2 = self.net.addSwitch(
            "a2",
            cls=OVSSwitch,
            dpid="0000000000000005",
            protocols=OPENFLOW_13_PROTOCOL,
        )
        a3 = self.net.addSwitch(
            "a3",
            cls=OVSSwitch,
            dpid="0000000000000006",
            protocols=OPENFLOW_13_PROTOCOL,
        )
        a4 = self.net.addSwitch(
            "a4",
            cls=OVSSwitch,
            dpid="0000000000000007",
            protocols=OPENFLOW_13_PROTOCOL,
        )

        logger.info(
            "[TOPOLOGY] Switches added: C1, D1, D2, A1, A2, A3, A4"
        )

        # Hosts.
        h1 = self.net.addHost("h1", ip=format_host_ip(1))
        h2 = self.net.addHost("h2", ip=format_host_ip(2))
        h3 = self.net.addHost("h3", ip=format_host_ip(3))
        h4 = self.net.addHost("h4", ip=format_host_ip(4))

        logger.info(
            "[TOPOLOGY] Hosts added: H1=%s H2=%s H3=%s H4=%s",
            format_host_ip(1),
            format_host_ip(2),
            format_host_ip(3),
            format_host_ip(4),
        )

        link_params = make_link_params(
            bw_mbps=self.link_bw_mbps,
            delay_ms=self.link_delay_ms,
        )

        # Host-to-access links.
        self.net.addLink(h1, a1, **link_params)
        self.net.addLink(h2, a2, **link_params)
        self.net.addLink(h3, a3, **link_params)
        self.net.addLink(h4, a4, **link_params)

        # Access-to-distribution links.
        self.net.addLink(a1, d1, **link_params)
        self.net.addLink(a2, d2, **link_params)
        self.net.addLink(a3, d1, **link_params)
        self.net.addLink(a4, d2, **link_params)

        # Distribution-to-core links.
        self.net.addLink(d1, c1, **link_params)
        self.net.addLink(c1, d2, **link_params)

        # Direct distribution link providing the alternate path.
        self.net.addLink(d1, d2, **link_params)

        logger.info(
            "[TOPOLOGY] Links added with bw=%dMbps delay=%s.",
            self.link_bw_mbps,
            self.link_delay_ms,
        )

        logger.info("[TOPOLOGY] Starting network...")
        self.net.start()
        logger.info("[TOPOLOGY] Network started.")

        switches = [c1, d1, d2, a1, a2, a3, a4]

        for switch in switches:
            configure_ovs_openflow13(switch)

        # Enable RSTP on the redundant core/distribution triangle so that
        # the physical redundancy remains available without an L2 loop.
        for switch in (c1, d1, d2):
            self.net.get(switch.name).cmd(
                "ovs-vsctl set bridge %s rstp_enable=true" % switch.name
            )
        logger.info("[TOPOLOGY] RSTP enabled on C1, D1, and D2.")

        failed_switches = [
            switch.name
            for switch in switches
            if not verify_openflow_version(switch)
        ]

        if failed_switches:
            logger.warning(
                "[TOPOLOGY] OpenFlow 1.3 could not be confirmed on: %s",
                ", ".join(failed_switches),
            )

        logger.info("[TOPOLOGY] Campus topology ready.")
        logger.info(
            "[TOPOLOGY] Redundant H1-H4 paths: "
            "H1-A1-D1-C1-D2-A4-H4 and H1-A1-D1-D2-A4-H4"
        )

    def run_pingall(self) -> float:
        """
        Run Mininet pingAll and return the packet drop percentage.
        """
        if self.net is None:
            raise RuntimeError("Network not built. Call build() first.")

        logger.info("[TOPOLOGY] Running pingAll connectivity test...")
        drop_pct = self.net.pingAll()

        if drop_pct == 0.0:
            logger.info("[TOPOLOGY] pingAll PASSED — 0%% packet drop.")
        else:
            logger.warning(
                "[TOPOLOGY] pingAll FAILED — %.1f%% packet drop.",
                drop_pct,
            )

        return drop_pct

    def run_cli(self) -> None:
        """
        Open the interactive Mininet CLI.
        """
        if self.net is None:
            raise RuntimeError("Network not built. Call build() first.")

        from mininet.cli import CLI

        logger.info("[TOPOLOGY] Entering Mininet CLI. Type 'exit' to quit.")
        CLI(self.net)

    def stop(self) -> None:
        """
        Stop the Mininet network safely.
        """
        if self.net is not None:
            logger.info("[TOPOLOGY] Stopping network...")
            self.net.stop()
            self.net = None
            logger.info("[TOPOLOGY] Network stopped.")
        else:
            logger.debug("[TOPOLOGY] stop() called but network was not running.")


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Redundant smart-campus Mininet topology",
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
        help="Link propagation delay",
    )

    parser.add_argument(
        "--pingall",
        action="store_true",
        help="Run pingAll after startup and exit",
    )

    parser.add_argument(
        "--no-cli",
        action="store_true",
        help="Do not open the interactive Mininet CLI",
    )

    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to config.yaml",
    )

    return parser.parse_args()


def main() -> int:
    """CLI entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    args = _parse_args()

    config = load_config(args.config)
    config_ip, config_port = get_controller_config(config)

    controller_ip = (
        args.controller_ip if args.controller_ip is not None else config_ip
    )
    controller_port = (
        args.controller_port
        if args.controller_port is not None
        else config_port
    )

    topology = CampusTopology(
        controller_ip=controller_ip,
        controller_port=controller_port,
        link_bw_mbps=args.bw,
        link_delay_ms=args.delay,
    )

    try:
        topology.build()

        if args.pingall:
            topology.run_pingall()

        if not args.no_cli:
            topology.run_cli()

    except KeyboardInterrupt:
        logger.info("[TOPOLOGY] Interrupted by user.")
    finally:
        topology.stop()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
