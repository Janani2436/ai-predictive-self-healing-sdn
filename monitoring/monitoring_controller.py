"""
monitoring/monitoring_controller.py
LINUX-SIMULATION-REQUIRED

Phase 6 — Network Monitoring.

Collects real OpenFlow 1.3 port statistics from OVS switches
through Ryu and writes interval measurements to CSV.

This module does not fabricate end-to-end delay or packet loss.
Those measurements must be collected separately from Mininet hosts.
"""

import csv
import logging
import os
import time
from datetime import datetime, timezone
from typing import Dict

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib import hub


logger = logging.getLogger(__name__)

OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

DEFAULT_POLL_INTERVAL = 5.0
DEFAULT_OUTPUT = "logs/monitoring/port_stats.csv"
DEFAULT_LINK_CAPACITY_MBPS = 100.0


class MonitoringController(app_manager.RyuApp):
    """
    Ryu OpenFlow 1.3 application for real-time port statistics collection.

    The controller periodically requests OFPPortStats from every connected
    switch and calculates transmit throughput and utilization from byte
    deltas between polling intervals.
    """

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.poll_interval = float(
            kwargs.get("poll_interval", DEFAULT_POLL_INTERVAL)
        )
        self.output_file = kwargs.get("output_file", DEFAULT_OUTPUT)
        self.link_capacity_mbps = float(
            kwargs.get("link_capacity_mbps", DEFAULT_LINK_CAPACITY_MBPS)
        )

        self.datapaths: Dict[int, object] = {}
        self.previous_stats: Dict[tuple, tuple] = {}

        self._prepare_output_file()

        self.monitor_thread = hub.spawn(self._monitor)

        logger.info(
            "[RYU] MonitoringController initialised: "
            "interval=%.2fs capacity=%.2fMbps output=%s",
            self.poll_interval,
            self.link_capacity_mbps,
            self.output_file,
        )

    def _prepare_output_file(self) -> None:
        """Create the monitoring CSV and header if it does not exist."""
        directory = os.path.dirname(self.output_file)

        if directory:
            os.makedirs(directory, exist_ok=True)

        if not os.path.exists(self.output_file):
            with open(self.output_file, "w", newline="", encoding="utf-8") as fh:
                writer = csv.writer(fh)
                writer.writerow([
                    "timestamp",
                    "switch",
                    "port",
                    "tx_bytes",
                    "rx_bytes",
                    "tx_throughput_mbps",
                    "rx_throughput_mbps",
                    "utilization_pct",
                ])

    @set_ev_cls(ofp_event.EventOFPStateChange, [CONFIG_DISPATCHER, MAIN_DISPATCHER])
    def state_change_handler(self, ev) -> None:
        """Track switches as they connect to and disconnect from Ryu."""
        datapath = ev.datapath

        if ev.state == MAIN_DISPATCHER:
            if datapath.id not in self.datapaths:
                self.datapaths[datapath.id] = datapath
                logger.info(
                    "[RYU] Monitoring switch connected: dpid=%s",
                    self._fmt_dpid(datapath.id),
                )

        elif ev.state == CONFIG_DISPATCHER:
            self.datapaths.pop(datapath.id, None)

    def _monitor(self) -> None:
        """Continuously request port statistics."""
        while True:
            for datapath in list(self.datapaths.values()):
                self._request_port_stats(datapath)

            hub.sleep(self.poll_interval)

    def _request_port_stats(self, datapath) -> None:
        """Send an OpenFlow port statistics request to one switch."""
        parser = datapath.ofproto_parser
        request = parser.OFPPortStatsRequest(
            datapath,
            0,
            datapath.ofproto.OFPP_ANY,
        )

        datapath.send_msg(request)

        logger.debug(
            "[OPENFLOW] Port statistics requested: dpid=%s",
            self._fmt_dpid(datapath.id),
        )

    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def port_stats_reply_handler(self, ev) -> None:
        """Process real OpenFlow port statistics."""
        datapath = ev.msg.datapath
        dpid = datapath.id
        now = time.monotonic()
        timestamp = datetime.now(timezone.utc).isoformat()

        rows = []

        for stat in ev.msg.body:
            port_no = stat.port_no

            if port_no >= datapath.ofproto.OFPP_MAX:
                continue

            key = (dpid, port_no)

            previous = self.previous_stats.get(key)

            self.previous_stats[key] = (
                now,
                stat.tx_bytes,
                stat.rx_bytes,
            )

            if previous is None:
                continue

            previous_time, previous_tx, previous_rx = previous
            interval = now - previous_time

            if interval <= 0:
                continue

            tx_delta = max(0, stat.tx_bytes - previous_tx)
            rx_delta = max(0, stat.rx_bytes - previous_rx)

            tx_mbps = (tx_delta * 8.0) / interval / 1_000_000
            rx_mbps = (rx_delta * 8.0) / interval / 1_000_000

            utilization_pct = (
                tx_mbps / self.link_capacity_mbps * 100.0
                if self.link_capacity_mbps > 0
                else 0.0
            )

            utilization_pct = min(100.0, max(0.0, utilization_pct))

            rows.append([
                timestamp,
                self._fmt_dpid(dpid),
                port_no,
                stat.tx_bytes,
                stat.rx_bytes,
                round(tx_mbps, 6),
                round(rx_mbps, 6),
                round(utilization_pct, 6),
            ])

        if rows:
            self._append_rows(rows)

    def _append_rows(self, rows) -> None:
        """Append monitoring measurements to the CSV."""
        with open(self.output_file, "a", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerows(rows)

        logger.info(
            "[MONITOR] Recorded %d port measurements",
            len(rows),
        )

    @staticmethod
    def _fmt_dpid(dpid: int) -> str:
        """Format a datapath ID consistently."""
        return f"{dpid:016x}"
