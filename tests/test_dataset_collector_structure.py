"""
WINDOWS-DEV-TESTED

Structural tests for Phase 7 dataset collection.
These tests do not require Mininet, OVS, Ryu, or Linux networking.
"""

import csv
import json

from experiments.dataset_collector import (
    DATASET_COLUMNS,
    build_dataset_rows,
    create_experiment_id,
    parse_ping_output,
    write_dataset,
    write_metadata,
)


def test_dataset_schema():
    expected = [
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

    assert DATASET_COLUMNS == expected


def test_create_experiment_id():
    experiment_id = create_experiment_id("normal")

    assert experiment_id.endswith("_normal")
    assert len(experiment_id) > len("_normal")


def test_parse_ping_output():
    output = """
    5 packets transmitted, 5 received, 0% packet loss, time 4004ms
    rtt min/avg/max/mdev = 1.100/2.200/3.300/0.400 ms
    """

    delay_ms, packet_loss_pct = parse_ping_output(output)

    assert delay_ms == 2.2
    assert packet_loss_pct == 0.0


def test_build_dataset_rows():
    monitoring_rows = [
        {
            "timestamp": "2026-10-08T10:00:00+00:00",
            "switch": "0000000000000004",
            "port": "1",
            "tx_throughput_mbps": "5.0",
            "utilization_pct": "5.0",
        }
    ]

    rows = build_dataset_rows(
        monitoring_rows=monitoring_rows,
        scenario="normal",
        source="h1",
        destination="h2",
        delay_ms=2.2,
        packet_loss_pct=0.0,
        traffic_rate_mbps=5.0,
        label="NORMAL",
    )

    assert len(rows) == 1
    assert rows[0]["source"] == "h1"
    assert rows[0]["destination"] == "h2"
    assert rows[0]["throughput_mbps"] == -1.0
    assert rows[0]["delay_ms"] == 2.2
    assert rows[0]["packet_loss_pct"] == 0.0
    assert rows[0]["traffic_rate_mbps"] == 5.0
    assert rows[0]["queue_length"] == -1
    assert rows[0]["link_status"] == -1
    assert rows[0]["label"] == "NORMAL"


def test_write_dataset(tmp_path):
    output_file = tmp_path / "experiment_test.csv"

    rows = [
        {
            "timestamp": "2026-10-08T10:00:00+00:00",
            "source": "h1",
            "destination": "h2",
            "switch": "0000000000000004",
            "port": "1",
            "throughput_mbps": 5.0,
            "delay_ms": 2.2,
            "packet_loss_pct": 0.0,
            "utilization_pct": 5.0,
            "traffic_rate_mbps": 5.0,
            "queue_length": -1,
            "link_status": -1,
            "label": "NORMAL",
        }
    ]

    write_dataset(str(output_file), rows)

    with open(output_file, newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        result = list(reader)

    assert reader.fieldnames == DATASET_COLUMNS
    assert len(result) == 1
    assert result[0]["label"] == "NORMAL"


def test_write_metadata(tmp_path):
    output_file = tmp_path / "experiment_test_meta.json"

    metadata = {
        "source": "mininet_experiment",
        "scenario": "normal",
        "label": "NORMAL",
        "queue_length": -1,
    }

    write_metadata(str(output_file), metadata)

    with open(output_file, encoding="utf-8") as file:
        result = json.load(file)

    assert result["source"] == "mininet_experiment"
    assert result["scenario"] == "normal"
    assert result["queue_length"] == -1
