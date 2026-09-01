"""
controller/simple_controller.py
LINUX-SIMULATION-REQUIRED

A minimal Ryu SDN controller application that implements:
  - OpenFlow 1.3 handshake and switch connection management
  - Table-miss flow entry installation
  - Reactive MAC learning and L2 forwarding
  - Basic flow rule installation via OFPFlowMod
  - Structured logging with [RYU] and [OPENFLOW] prefixes

This is Phase 3 of the AI-Driven Predictive Self-Healing SDN project.
It provides the foundation on which monitoring, ML prediction, and
self-healing components will be built in later phases.

This file does NOT include:
  - Port statistics collection (Phase 6 — monitoring_controller.py)
  - ML prediction integration (Phase 8+)
  - Health scoring or path optimization (Phase 9/10)
  - Predictive rerouting (Phase 12)

Usage (Ubuntu simulation machine only):
    ryu-manager controller/simple_controller.py \\
        --observe-links \\
        --ofp-tcp-listen-port 6633

Then start the Mininet topology in a separate terminal:
    sudo python topology/simple_topology.py

LINUX-SIMULATION-REQUIRED
This module requires Ryu and a Linux OpenFlow socket.
It cannot be executed on the Windows development machine.

Compatibility:
    Ryu:      faucetsdn/ryu (git) or ryu==4.34 from PyPI
    Python:   3.10 (Ubuntu 22.04 LTS recommended)
    eventlet: 0.33.3 (pinned — see docs/ryu_compatibility.md)
    OVS:      2.17.x (Ubuntu 22.04 apt)
    OpenFlow: 1.3
"""

# LINUX-SIMULATION-REQUIRED
# This module requires Ryu running on Ubuntu with OVS.
# Importing this module on Windows will succeed (Ryu is not imported at
# module level), but instantiating or running the app will fail.

import logging
from collections import defaultdict
from typing import Optional

# Ryu imports are at module level because this file IS the Ryu application.
# The import will fail on Windows where Ryu is not installed — this is
# expected and correct. Do not add try/except around these imports.
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.lib.packet import ethernet, packet, ether_types
from ryu.ofproto import ofproto_v1_3

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants — all tunable values come from here, never hard-coded in logic
# ---------------------------------------------------------------------------

# OpenFlow version declaration — used by Ryu to negotiate the protocol version
OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

# Flow table priorities
PRIORITY_TABLE_MISS = 0          # lowest — matched only when nothing else does
PRIORITY_LEARNED_FLOW = 1        # normal forwarding flows

# Flow timeouts (seconds)
IDLE_TIMEOUT = 30                # remove flow if no matching packets for this long
HARD_TIMEOUT = 120               # remove flow unconditionally after this long
# 0 means permanent; avoid permanent flows for L2 learning to prevent loops

# Flood port (OpenFlow constant for "send to all ports except ingress")
# Using ofproto.OFPP_FLOOD avoids hard-coding the port number.


# ---------------------------------------------------------------------------
# Controller application
# ---------------------------------------------------------------------------

class SimpleController(app_manager.RyuApp):
    """
    Minimal Ryu OpenFlow 1.3 controller with MAC learning.

    Implements:
        - Switch connection and feature negotiation (CONFIG_DISPATCHER)
        - Table-miss flow entry installation
        - Reactive MAC address learning
        - Unicast forwarding when destination MAC is known
        - Flooding when destination MAC is unknown

    This controller is intentionally minimal. It proves the full
    Ryu → OVS → OpenFlow 1.3 path works before adding monitoring and ML.
    """

    # Declare the OpenFlow version(s) this app supports.
    # Ryu will negotiate OF1.3 with each connecting switch.
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs) -> None:
        """Initialise controller state."""
        super().__init__(*args, **kwargs)

        # MAC address table: {datapath_id -> {mac_address -> port_number}}
        # Populated reactively as packets arrive.
        self.mac_to_port: dict[int, dict[str, int]] = defaultdict(dict)

        logger.info("[RYU] SimpleController initialised. Waiting for switches.")

    # ── Switch connection ──────────────────────────────────────────────────────

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev) -> None:
        """
        Handle new switch connection.

        Called when a switch connects and sends its feature reply.
        Installs the table-miss flow entry that sends unmatched packets
        to the controller via PACKET_IN.

        Args:
            ev: Ryu event carrying the OFPSwitchFeatures message.
        """
        datapath = ev.msg.datapath
        dpid = datapath.id
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        logger.info(
            "[RYU] Switch connected: dpid=%s  OF version=%s",
            self._fmt_dpid(dpid),
            datapath.ofproto.OFP_VERSION,
        )

        # Install table-miss entry: match everything, priority 0,
        # action = send to controller (OFPP_CONTROLLER), no hard timeout.
        # This ensures that packets with no matching flow rule are sent up
        # to this controller for learning.
        match = parser.OFPMatch()
        actions = [
            parser.OFPActionOutput(
                ofproto.OFPP_CONTROLLER,
                ofproto.OFPCML_NO_BUFFER,  # send entire packet, no buffering
            )
        ]
        self._install_flow(
            datapath=datapath,
            priority=PRIORITY_TABLE_MISS,
            match=match,
            actions=actions,
            idle_timeout=0,   # permanent — table-miss must always exist
            hard_timeout=0,
        )
        logger.info(
            "[OPENFLOW] Table-miss flow installed on dpid=%s", self._fmt_dpid(dpid)
        )

    # ── Packet-in handler ──────────────────────────────────────────────────────

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev) -> None:
        """
        Handle PACKET_IN messages from switches.

        For each incoming packet:
          1. Learn the source MAC → ingress port mapping.
          2. If the destination MAC is known: install a flow rule and
             forward this packet directly.
          3. If the destination MAC is unknown: flood to all ports.

        Args:
            ev: Ryu event carrying the OFPPacketIn message.
        """
        msg = ev.msg
        datapath = msg.datapath
        dpid = datapath.id
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # In_port is carried in the match field of the PacketIn message
        in_port = msg.match["in_port"]

        # Parse the raw packet bytes into layers
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        # Ignore LLDP frames — used by Ryu's topology discovery, not forwarding
        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return

        dst_mac = eth.dst
        src_mac = eth.src

        logger.debug(
            "[MONITOR] PACKET_IN dpid=%s port=%d src=%s dst=%s",
            self._fmt_dpid(dpid), in_port, src_mac, dst_mac,
        )

        # ── Step 1: MAC learning ───────────────────────────────────────────────
        # Record that src_mac was seen arriving on in_port of this switch
        if self.mac_to_port[dpid].get(src_mac) != in_port:
            logger.info(
                "[RYU] Learned: dpid=%s  mac=%s → port=%d",
                self._fmt_dpid(dpid), src_mac, in_port,
            )
        self.mac_to_port[dpid][src_mac] = in_port

        # ── Step 2: Determine output port ─────────────────────────────────────
        if dst_mac in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst_mac]
        else:
            out_port = ofproto.OFPP_FLOOD  # unknown destination → flood

        actions = [parser.OFPActionOutput(out_port)]

        # ── Step 3: Install flow rule (if destination is known) ───────────────
        # Only install a flow when we know the exact port — never install a
        # flood flow (that would cause packet storms).
        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst_mac, eth_src=src_mac)
            # Use buffer_id if the switch buffered the packet, to avoid
            # sending the packet data twice
            if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                self._install_flow(
                    datapath=datapath,
                    priority=PRIORITY_LEARNED_FLOW,
                    match=match,
                    actions=actions,
                    idle_timeout=IDLE_TIMEOUT,
                    hard_timeout=HARD_TIMEOUT,
                    buffer_id=msg.buffer_id,
                )
                # Packet already sent by the switch via buffer — we are done
                logger.info(
                    "[OPENFLOW] Flow installed: dpid=%s  %s → port=%d  (buffered)",
                    self._fmt_dpid(dpid), dst_mac, out_port,
                )
                return
            else:
                self._install_flow(
                    datapath=datapath,
                    priority=PRIORITY_LEARNED_FLOW,
                    match=match,
                    actions=actions,
                    idle_timeout=IDLE_TIMEOUT,
                    hard_timeout=HARD_TIMEOUT,
                )
                logger.info(
                    "[OPENFLOW] Flow installed: dpid=%s  %s → port=%d",
                    self._fmt_dpid(dpid), dst_mac, out_port,
                )

        # ── Step 4: Send this specific packet out ──────────────────────────────
        # Required when: (a) flooding, or (b) flow installed but no buffer_id
        self._send_packet_out(
            datapath=datapath,
            buffer_id=msg.buffer_id,
            in_port=in_port,
            actions=actions,
            data=msg.data,
        )

    # ── OpenFlow helpers ───────────────────────────────────────────────────────

    def _install_flow(
        self,
        datapath,
        priority: int,
        match,
        actions: list,
        idle_timeout: int = IDLE_TIMEOUT,
        hard_timeout: int = HARD_TIMEOUT,
        buffer_id: Optional[int] = None,
    ) -> None:
        """
        Install a flow rule on a switch via OFPFlowMod.

        Args:
            datapath:     The switch to install the flow on.
            priority:     Match priority (higher = checked first).
            match:        OFPMatch object specifying the matching criteria.
            actions:      List of OFPAction objects.
            idle_timeout: Seconds of inactivity before removal (0 = permanent).
            hard_timeout: Seconds until forced removal (0 = permanent).
            buffer_id:    Switch buffer ID if packet was buffered, else None.
        """
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # Wrap actions in an instruction (APPLY_ACTIONS)
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]

        kwargs = {
            "datapath": datapath,
            "priority": priority,
            "match": match,
            "instructions": inst,
            "idle_timeout": idle_timeout,
            "hard_timeout": hard_timeout,
        }

        if buffer_id is not None and buffer_id != ofproto.OFP_NO_BUFFER:
            kwargs["buffer_id"] = buffer_id

        mod = parser.OFPFlowMod(**kwargs)
        datapath.send_msg(mod)

        logger.debug(
            "[OPENFLOW] OFPFlowMod sent to dpid=%s  priority=%d",
            self._fmt_dpid(datapath.id), priority,
        )

    def _send_packet_out(
        self,
        datapath,
        buffer_id: int,
        in_port: int,
        actions: list,
        data: Optional[bytes],
    ) -> None:
        """
        Send an OFPPacketOut to forward a specific packet.

        Used when flooding or when a flow was installed without a buffer_id.

        Args:
            datapath:  The switch.
            buffer_id: Switch buffer ID (OFP_NO_BUFFER if not buffered).
            in_port:   Port the packet arrived on.
            actions:   Output action(s).
            data:      Raw packet bytes (only needed if not buffered).
        """
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        if buffer_id != ofproto.OFP_NO_BUFFER:
            out = parser.OFPPacketOut(
                datapath=datapath,
                buffer_id=buffer_id,
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
                data=data,
            )

        datapath.send_msg(out)

    # ── Utility ────────────────────────────────────────────────────────────────

    @staticmethod
    def _fmt_dpid(dpid: int) -> str:
        """Format a datapath ID as a zero-padded hex string for readability."""
        return f"{dpid:016x}"
