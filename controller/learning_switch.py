"""
controller/learning_switch.py
LINUX-SIMULATION-REQUIRED

A standalone Ryu MAC-learning L2 switch application.

This module can be run independently as a Ryu app to verify that the
Ryu + OVS + OpenFlow 1.3 stack is working before integrating the
monitoring and prediction layers.

Difference from simple_controller.py:
    - simple_controller.py is the primary controller for this project.
      It is designed to be extended with monitoring and ML components.
    - learning_switch.py is a self-contained, single-file reference
      implementation. It is useful for:
        (a) Verifying Ryu + OVS baseline connectivity in isolation
        (b) Running as the "baseline / conventional SDN" comparator
            in experiments (Phase 14)
        (c) Debugging — if simple_controller.py has a problem, running
            this file quickly identifies whether the issue is in the
            base Ryu layer or in the project-specific code

Usage (Ubuntu simulation machine only):
    # Verify baseline (standalone — no project imports needed)
    ryu-manager controller/learning_switch.py \\
        --ofp-tcp-listen-port 6633

    # Run as baseline for experiment comparison
    ryu-manager controller/learning_switch.py \\
        --ofp-tcp-listen-port 6633 \\
        --config-file config.yaml

LINUX-SIMULATION-REQUIRED
Requires Ryu on Ubuntu. Cannot execute on Windows development machine.

Compatibility:
    Ryu:      faucetsdn/ryu (git) or ryu==4.34 from PyPI
    Python:   3.10 (Ubuntu 22.04 LTS recommended)
    eventlet: 0.33.3 (pinned)
    OpenFlow: 1.3
"""

# LINUX-SIMULATION-REQUIRED
# This module requires Ryu running on Ubuntu with OVS.

import logging
from collections import defaultdict

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.lib.packet import ethernet, packet, ether_types
from ryu.ofproto import ofproto_v1_3

logger = logging.getLogger(__name__)


class LearningSwitch(app_manager.RyuApp):
    """
    Standalone Ryu MAC-learning L2 switch for baseline comparison.

    Implements reactive MAC learning and L2 unicast forwarding over
    OpenFlow 1.3. This is a conventional (non-predictive) SDN controller
    used as the baseline in performance comparison experiments.

    Behaviour:
        1. On switch connect: install table-miss entry (priority=0).
        2. On PACKET_IN: learn source MAC → port.
        3. If destination MAC known: install forward flow + unicast packet.
        4. If destination MAC unknown: flood packet.
        5. No prediction, no health scoring, no proactive rerouting.

    This represents a standard reactive SDN controller. It detects problems
    only after they are already affecting traffic, which is the behaviour
    the AI-driven system is designed to improve upon.

    Verification status: LINUX-SIMULATION-REQUIRED
    """

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    # Flow priorities
    _PRIORITY_MISS = 0
    _PRIORITY_FORWARD = 1

    # Flow timeouts
    _IDLE_TIMEOUT = 30
    _HARD_TIMEOUT = 120

    def __init__(self, *args, **kwargs) -> None:
        """Initialise MAC address table."""
        super().__init__(*args, **kwargs)
        # {dpid -> {mac -> port}}
        self.mac_to_port: dict[int, dict[str, int]] = defaultdict(dict)
        logger.info("[RYU] LearningSwitch (baseline) initialised.")

    # ── Switch connect ─────────────────────────────────────────────────────────

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def _switch_features_handler(self, ev) -> None:
        """
        Install the table-miss flow entry when a switch connects.

        The table-miss entry (priority=0, match-all) sends unmatched
        packets to the controller so MAC learning can take place.
        """
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        logger.info(
            "[RYU] Switch connected: dpid=%s",
            format(datapath.id, "016x"),
        )

        match = parser.OFPMatch()
        actions = [
            parser.OFPActionOutput(
                ofproto.OFPP_CONTROLLER,
                ofproto.OFPCML_NO_BUFFER,
            )
        ]
        self._add_flow(
            datapath,
            priority=self._PRIORITY_MISS,
            match=match,
            actions=actions,
            idle_timeout=0,
            hard_timeout=0,
        )
        logger.info(
            "[OPENFLOW] Table-miss flow installed: dpid=%s",
            format(datapath.id, "016x"),
        )

    # ── Packet-in ──────────────────────────────────────────────────────────────

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev) -> None:
        """
        Reactive MAC learning and L2 forwarding.

        For each PACKET_IN:
          1. Learn source MAC → ingress port.
          2. Forward to known port or flood if unknown.
          3. Install a flow rule when destination is known.
        """
        msg = ev.msg
        datapath = msg.datapath
        dpid = datapath.id
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match["in_port"]

        pkt = packet.Packet(msg.data)
        eth_pkt = pkt.get_protocols(ethernet.ethernet)[0]

        if eth_pkt.ethertype == ether_types.ETH_TYPE_LLDP:
            return  # ignore topology discovery frames

        dst = eth_pkt.dst
        src = eth_pkt.src

        # MAC learning
        self.mac_to_port[dpid][src] = in_port

        # Port lookup
        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD

        actions = [parser.OFPActionOutput(out_port)]

        # Install flow when destination port is known
        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(
                in_port=in_port,
                eth_dst=dst,
                eth_src=src,
            )
            if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                self._add_flow(
                    datapath,
                    priority=self._PRIORITY_FORWARD,
                    match=match,
                    actions=actions,
                    idle_timeout=self._IDLE_TIMEOUT,
                    hard_timeout=self._HARD_TIMEOUT,
                    buffer_id=msg.buffer_id,
                )
                return  # switch already forwarded the buffered packet
            else:
                self._add_flow(
                    datapath,
                    priority=self._PRIORITY_FORWARD,
                    match=match,
                    actions=actions,
                    idle_timeout=self._IDLE_TIMEOUT,
                    hard_timeout=self._HARD_TIMEOUT,
                )

        # Send this packet out
        if msg.buffer_id != ofproto.OFP_NO_BUFFER:
            out = parser.OFPPacketOut(
                datapath=datapath,
                buffer_id=msg.buffer_id,
                in_port=in_port,
                actions=actions,
                data=None,
            )
        else:
            out = parser.OFPPacketOut(
                datapath=datapath,
                buffer_id=ofproto.OFP_NO_BUFFER,
                in_port=in_port,
                actions=actions,
                data=msg.data,
            )
        datapath.send_msg(out)

    # ── Helper ─────────────────────────────────────────────────────────────────

    def _add_flow(
        self,
        datapath,
        priority: int,
        match,
        actions: list,
        idle_timeout: int = 0,
        hard_timeout: int = 0,
        buffer_id: int | None = None,
    ) -> None:
        """
        Send an OFPFlowMod to install a flow rule on a switch.

        Args:
            datapath:     Target switch.
            priority:     Match priority.
            match:        OFPMatch criteria.
            actions:      Output action(s).
            idle_timeout: Remove after N seconds idle (0 = permanent).
            hard_timeout: Remove after N seconds total (0 = permanent).
            buffer_id:    Switch buffer ID if packet was buffered.
        """
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [
            parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)
        ]

        kwargs: dict = dict(
            datapath=datapath,
            priority=priority,
            match=match,
            instructions=inst,
            idle_timeout=idle_timeout,
            hard_timeout=hard_timeout,
        )
        if buffer_id is not None and buffer_id != ofproto.OFP_NO_BUFFER:
            kwargs["buffer_id"] = buffer_id

        datapath.send_msg(parser.OFPFlowMod(**kwargs))
