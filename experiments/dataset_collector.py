"""
experiments/dataset_collector.py

LINUX-SIMULATION-REQUIRED

Phase 7 — Real experiment dataset collection.

Combines:
    - Ryu OpenFlow port statistics
    - Mininet end-to-end ping measurements
    - receiver-side iperf3 measurements

No performance values are fabricated.
Unavailable measurements are recorded as -1.
"""

import argparse
import csv
import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from typing import Any


logger = logging.getLogger(__name__)


DATASET_COLUMNS = [
    "timestamp",
    "source",
    "destination",
    "switch",
    "port",
    "throughput_mbps",
    "delay_ms",
    "packet_loss_pct",
    "utilization_pct",
    "traffic_rate_mbps",
    "queue_length",
    "link_status",
    "label",
]


def create_experiment_id(scenario: str) -> str:
    """Create a UTC timestamped experiment identifier."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"{timestamp}_{scenario}"


def parse_ping_output(output: str) -> tuple[float, float]:
    """
    Parse Linux ping output.

    Returns:
        (delay_ms, packet_loss_pct)
    """
    loss_match = re.search(
        r"(\d+(?:\.\d+)?)%\s*packet loss",
        output,
    )

    rtt_match = re.search(
        r"(?:rtt|round-trip).*=\s*"
        r"([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+)\s*ms",
        output,
    )

    if loss_match is None:
        raise ValueError(
            "Could not parse packet loss from ping output"
        )

    if rtt_match is None:
        raise ValueError(
            "Could not parse RTT from ping output"
        )

    return (
        float(rtt_match.group(2)),
        float(loss_match.group(1)),
    )


def measure_ping(
    source: Any,
    destination_ip: str,
    count: int = 5,
) -> dict[str, float]:
    """
    Run ping from a Mininet host to another host.
    """
    if count <= 0:
        raise ValueError(
            "count must be greater than zero"
        )

    output = source.cmd(
        "ping",
        "-c",
        str(count),
        "-W",
        "1",
        destination_ip,
    )

    delay_ms, packet_loss_pct = parse_ping_output(output)

    logger.info(
        "[DATASET] Ping %s -> %s: delay=%.3fms loss=%.3f%%",
        source.name,
        destination_ip,
        delay_ms,
        packet_loss_pct,
    )

    return {
        "delay_ms": delay_ms,
        "packet_loss_pct": packet_loss_pct,
    }


def read_monitoring_rows(
    monitoring_file: str,
    start_time: float,
    end_time: float,
) -> list[dict[str, str]]:
    """
    Read OpenFlow monitoring rows whose timestamps fall inside
    the experiment measurement window.
    """
    if not os.path.exists(monitoring_file):
        raise FileNotFoundError(
            f"Monitoring file not found: {monitoring_file}"
        )

    rows = []

    with open(
        monitoring_file,
        "r",
        newline="",
        encoding="utf-8",
    ) as file:
        reader = csv.DictReader(file)

        for row in reader:
            timestamp_text = row.get("timestamp", "")

            if not timestamp_text:
                continue

            try:
                timestamp = datetime.fromisoformat(
                    timestamp_text
                ).timestamp()
            except ValueError:
                continue

            if start_time <= timestamp <= end_time:
                rows.append(row)

    return rows


def get_receiver_stats(
    traffic_result: dict[str, Any] | None,
) -> dict[str, float]:
    """
    Extract validated receiver-side iperf3 statistics.

    Returns -1 for unavailable values rather than fabricating data.
    """
    if not traffic_result:
        return {
            "throughput_mbps": -1.0,
            "packet_loss_pct": -1.0,
            "jitter_ms": -1.0,
        }

    receiver_stats = traffic_result.get(
        "receiver_stats"
    )

    if not isinstance(receiver_stats, dict):
        return {
            "throughput_mbps": -1.0,
            "packet_loss_pct": -1.0,
            "jitter_ms": -1.0,
        }

    return {
        "throughput_mbps": float(
            receiver_stats.get(
                "throughput_mbps",
                -1.0,
            )
        ),
        "packet_loss_pct": float(
            receiver_stats.get(
                "loss_pct",
                -1.0,
            )
        ),
        "jitter_ms": float(
            receiver_stats.get(
                "jitter_ms",
                -1.0,
            )
        ),
    }


def build_dataset_rows(
    monitoring_rows: list[dict[str, str]],
    scenario: str,
    source: str,
    destination: str,
    delay_ms: float,
    packet_loss_pct: float,
    traffic_rate_mbps: float,
    label: str,
    receiver_throughput_mbps: float = -1.0,
    receiver_packet_loss_pct: float = -1.0,
) -> list[dict[str, Any]]:
    """
    Combine actual OpenFlow and end-to-end measurements.

    `throughput_mbps` represents receiver-side iperf3 throughput
    when available.

    OpenFlow TX throughput remains available through the source
    monitoring file but is not incorrectly presented as
    end-to-end throughput.
    """
    rows = []

    for monitoring_row in monitoring_rows:
        timestamp = monitoring_row["timestamp"]

        rows.append(
            {
                "timestamp": timestamp,
                "source": source,
                "destination": destination,
                "switch": monitoring_row["switch"],
                "port": monitoring_row["port"],
                "throughput_mbps": receiver_throughput_mbps,
                "delay_ms": delay_ms,
                "packet_loss_pct": (
                    receiver_packet_loss_pct
                    if receiver_packet_loss_pct >= 0
                    else packet_loss_pct
                ),
                "utilization_pct": monitoring_row[
                    "utilization_pct"
                ],
                "traffic_rate_mbps": traffic_rate_mbps,
                "queue_length": -1,
                "link_status": -1,
                "label": label,
            }
        )

    return rows


def collect_experiment(
    network: Any,
    scenario: str,
    source: Any,
    destination: Any,
    monitoring_file: str = "logs/monitoring/port_stats.csv",
    output_dir: str = "dataset/raw",
    ping_count: int = 5,
    traffic_result: dict[str, Any] | None = None,
    traffic_rate_mbps: float = -1.0,
    label: str = "NORMAL",
    wait_seconds: float = 1.0,
    measurement_start_time: float | None = None,
    measurement_end_time: float | None = None,
) -> tuple[str, str]:
    """
    Collect one dataset segment from an active Mininet experiment.

    The actual traffic scenario must already have been executed.
    `traffic_result` should contain receiver-side iperf3 data.
    """
    del network

    if not scenario.strip():
        raise ValueError("scenario cannot be empty")

    if not label.strip():
        raise ValueError("label cannot be empty")

    if wait_seconds < 0:
        raise ValueError(
            "wait_seconds cannot be negative"
        )

    experiment_id = create_experiment_id(scenario)

    experiment_start = (
        time.time()
        if measurement_start_time is None
        else measurement_start_time
    )

    if wait_seconds:
        time.sleep(wait_seconds)

    ping_result = measure_ping(
        source=source,
        destination_ip=destination.IP(),
        count=ping_count,
    )

    experiment_end = (
        time.time()
        if measurement_end_time is None
        else measurement_end_time
    )

    if experiment_end < experiment_start:
        raise ValueError(
            "measurement_end_time cannot precede "
            "measurement_start_time"
        )

    monitoring_rows = read_monitoring_rows(
        monitoring_file=monitoring_file,
        start_time=experiment_start,
        end_time=experiment_end,
    )

    if not monitoring_rows:
        raise RuntimeError(
            "No monitoring samples found inside the experiment "
            "window. Check that Ryu is recording fresh port "
            "statistics. No dataset was saved."
        )

    receiver_stats = get_receiver_stats(
        traffic_result
    )

    if traffic_rate_mbps < 0 and traffic_result:
        result_rate = traffic_result.get(
            "rate_mbps"
        )

        if result_rate is not None:
            traffic_rate_mbps = float(
                result_rate
            )

    rows = build_dataset_rows(
        monitoring_rows=monitoring_rows,
        scenario=scenario,
        source=source.name,
        destination=destination.name,
        delay_ms=ping_result["delay_ms"],
        packet_loss_pct=ping_result[
            "packet_loss_pct"
        ],
        traffic_rate_mbps=traffic_rate_mbps,
        label=label,
        receiver_throughput_mbps=receiver_stats[
            "throughput_mbps"
        ],
        receiver_packet_loss_pct=receiver_stats[
            "packet_loss_pct"
        ],
    )

    csv_file = os.path.join(
        output_dir,
        f"experiment_{experiment_id}.csv",
    )

    metadata_file = os.path.join(
        output_dir,
        f"experiment_{experiment_id}_meta.json",
    )

    write_dataset(
        output_file=csv_file,
        rows=rows,
    )

    metadata = {
        "source": "mininet_experiment",
        "experiment_id": experiment_id,
        "date": datetime.now(
            timezone.utc
        ).isoformat(),
        "topology": "campus",
        "scenario": scenario,
        "duration_seconds": round(
            experiment_end - experiment_start,
            3,
        ),
        "controller": "monitoring_controller.py",
        "monitoring_file": monitoring_file,
        "source_host": source.name,
        "destination_host": destination.name,
        "destination_ip": destination.IP(),
        "ping_count": ping_count,
        "measured_delay_ms": ping_result[
            "delay_ms"
        ],
        "ping_packet_loss_pct": ping_result[
            "packet_loss_pct"
        ],
        "receiver_throughput_mbps": receiver_stats[
            "throughput_mbps"
        ],
        "receiver_packet_loss_pct": receiver_stats[
            "packet_loss_pct"
        ],
        "receiver_jitter_ms": receiver_stats[
            "jitter_ms"
        ],
        "traffic_rate_mbps": traffic_rate_mbps,
        "label": label,
        "monitoring_rows": len(monitoring_rows),
        "dataset_rows": len(rows),
        "queue_length": -1,
        "link_status": -1,
        "feature_availability": {
            "utilization_pct": "Measured from Ryu OpenFlow port statistics",
            "throughput_mbps": "Receiver-side iperf3 measurement; -1 means unavailable",
            "delay_ms": "Post-scenario ping average repeated across rows",
            "packet_loss_pct": "Receiver-side iperf3 loss when available; otherwise ping loss",
            "queue_length": "Not measured; -1 means unavailable",
            "link_status": "Not measured; -1 means unavailable",
        },
        "notes": (
            "Rows combine port-level OpenFlow monitoring samples "
            "with flow-level measurements. Receiver throughput and "
            "UDP packet loss come from iperf3 when available. "
            "Ping delay is measured after the traffic scenario and "
            "repeated across that flow's rows; it is not a per-row "
            "latency measurement. Queue length and link status are "
            "not measured and are recorded as -1. Do not treat "
            "repeated flow measurements as independent observations."
        ),
    }

    write_metadata(
        metadata_file=metadata_file,
        metadata=metadata,
    )

    return csv_file, metadata_file


def write_dataset(
    output_file: str,
    rows: list[dict[str, Any]],
) -> None:
    """Write dataset rows using the required schema."""
    directory = os.path.dirname(output_file)

    if directory:
        os.makedirs(directory, exist_ok=True)

    with open(
        output_file,
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=DATASET_COLUMNS,
        )

        writer.writeheader()
        writer.writerows(rows)

    logger.info(
        "[DATASET] Wrote %d rows to %s",
        len(rows),
        output_file,
    )


def write_metadata(
    metadata_file: str,
    metadata: dict[str, Any],
) -> None:
    """Write experiment provenance metadata."""
    directory = os.path.dirname(metadata_file)

    if directory:
        os.makedirs(directory, exist_ok=True)

    with open(
        metadata_file,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            metadata,
            file,
            indent=2,
        )

    logger.info(
        "[DATASET] Wrote metadata to %s",
        metadata_file,
    )


def configure_logging() -> None:
    """Configure console logging."""
    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s %(levelname)s "
            "%(name)s: %(message)s"
        ),
    )


def parse_arguments() -> argparse.Namespace:
    """Parse structural command-line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Collect real Mininet measurements into a Phase 7 "
            "dataset."
        )
    )

    parser.add_argument(
        "--monitoring-file",
        default="logs/monitoring/port_stats.csv",
    )

    parser.add_argument(
        "--output-dir",
        default="dataset/raw",
    )

    parser.add_argument(
        "--scenario",
        default="normal",
    )

    parser.add_argument(
        "--label",
        default="NORMAL",
    )

    parser.add_argument(
        "--ping-count",
        type=int,
        default=5,
    )

    return parser.parse_args()


def main() -> int:
    """
    Dataset collector entry point.

    Direct execution is intentionally not supported because
    an active CampusTopology network and traffic scenario are
    required.
    """
    configure_logging()
    parse_arguments()

    logger.info(
        "[DATASET] Dataset collector module loaded."
    )
    logger.info(
        "[DATASET] An active Mininet experiment is required "
        "for collection."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
