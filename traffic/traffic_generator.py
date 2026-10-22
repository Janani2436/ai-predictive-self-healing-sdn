"""
traffic/traffic_generator.py

LINUX-SIMULATION-REQUIRED

Utilities for generating and recording iperf3 traffic
inside the Mininet smart-campus simulation.
"""

import json
import logging
import re
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

    The client requests server-side JSON output so receiver-side
    UDP measurements can be preserved in the returned JSON.
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
        "--get-server-output",
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


def extract_receiver_udp_stats(
    iperf_result: dict,
) -> dict[str, float] | None:
    """
    Extract receiver-side UDP measurements from iperf3 JSON.

    Supports both:
    - server_output_json, when provided by iperf3
    - server_output_text, which is the format observed in the
      actual Mininet iperf3 3.9 experiment

    Receiver throughput is taken from the final aggregate
    receiver line in server output text. No values are inferred
    when receiver data is unavailable.
    """
    server_output = iperf_result.get("server_output_json")

    if isinstance(server_output, dict):
        end = server_output.get("end")

        if isinstance(end, dict):
            streams = end.get("streams", [])

            if isinstance(streams, list) and streams:
                receiver_streams = []

                for stream in streams:
                    if not isinstance(stream, dict):
                        continue

                    udp = stream.get("udp")

                    if not isinstance(udp, dict):
                        continue

                    if udp.get("sender") is False:
                        receiver_streams.append(udp)

                if receiver_streams:
                    receiver_packets = sum(
                        float(stream.get("packets", 0))
                        for stream in receiver_streams
                    )

                    receiver_lost_packets = sum(
                        float(stream.get("lost_packets", 0))
                        for stream in receiver_streams
                    )

                    receiver_jitter_values = [
                        float(stream["jitter_ms"])
                        for stream in receiver_streams
                        if "jitter_ms" in stream
                    ]

                    intervals = server_output.get(
                        "intervals",
                        [],
                    )

                    throughput_values = []

                    if isinstance(intervals, list):
                        for interval in intervals:
                            if not isinstance(interval, dict):
                                continue

                            sums = interval.get("sum")

                            if not isinstance(sums, dict):
                                continue

                            if sums.get("sender") is False:
                                bits_per_second = sums.get(
                                    "bits_per_second"
                                )

                                if bits_per_second is not None:
                                    throughput_values.append(
                                        float(bits_per_second)
                                    )

                    if throughput_values:
                        return {
                            "throughput_mbps": (
                                throughput_values[-1] / 1_000_000
                            ),
                            "packets": receiver_packets,
                            "lost_packets": (
                                receiver_lost_packets
                            ),
                            "loss_pct": (
                                receiver_lost_packets
                                / (
                                    receiver_packets
                                    + receiver_lost_packets
                                )
                                * 100.0
                                if (
                                    receiver_packets
                                    + receiver_lost_packets
                                ) > 0
                                else 0.0
                            ),
                            "jitter_ms": (
                                sum(receiver_jitter_values)
                                / len(receiver_jitter_values)
                                if receiver_jitter_values
                                else -1.0
                            ),
                        }

    server_text = iperf_result.get(
        "server_output_text"
    )

    if not isinstance(server_text, str):
        return None

    receiver_pattern = re.compile(
        r"\[\s*\d+\]\s+"
        r"[\d.]+-[\d.]+\s+sec\s+"
        r"[\d.]+\s+"
        r"(?:K|M|G)Bytes\s+"
        r"([\d.]+)\s+Mbits/sec\s+"
        r"([\d.]+)\s+ms\s+"
        r"(\d+)/(\d+)\s+"
        r"\([\d.]+%\)\s+receiver"
    )

    match = receiver_pattern.search(server_text)

    if match is None:
        return None

    throughput_mbps = float(match.group(1))
    jitter_ms = float(match.group(2))
    lost_packets = int(match.group(3))
    total_packets = int(match.group(4))

    loss_pct = (
        lost_packets / total_packets * 100.0
        if total_packets > 0
        else 0.0
    )

    return {
        "throughput_mbps": throughput_mbps,
        "packets": total_packets,
        "lost_packets": lost_packets,
        "loss_pct": loss_pct,
        "jitter_ms": jitter_ms,
    }

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

    if isinstance(result["iperf3"], dict):
        receiver_stats = extract_receiver_udp_stats(
            result["iperf3"]
        )

        result["receiver_stats"] = receiver_stats

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
