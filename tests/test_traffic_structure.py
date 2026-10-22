"""
Structural tests for Phase 5 traffic-generation modules.
"""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

TRAFFIC_GENERATOR = (
    PROJECT_ROOT / "traffic" / "traffic_generator.py"
)

NORMAL_TRAFFIC = (
    PROJECT_ROOT / "traffic" / "normal_traffic.py"
)

CONGESTION_SCENARIO = (
    PROJECT_ROOT / "traffic" / "congestion_scenario.py"
)

PHASE5_RUNNER = (
    PROJECT_ROOT / "traffic" / "phase5_runner.py"
)


def test_traffic_generator_exists():
    assert TRAFFIC_GENERATOR.exists()


def test_normal_traffic_exists():
    assert NORMAL_TRAFFIC.exists()


def test_congestion_scenario_exists():
    assert CONGESTION_SCENARIO.exists()


def test_phase5_runner_exists():
    assert PHASE5_RUNNER.exists()


def test_traffic_generator_has_required_functions():
    source = TRAFFIC_GENERATOR.read_text(
        encoding="utf-8"
    )

    required_functions = [
        "start_iperf_server",
        "stop_iperf_server",
        "start_iperf_client",
        "run_iperf_client",
        "save_traffic_result",
        "wait_for_server",
    ]

    for function_name in required_functions:
        assert f"def {function_name}(" in source


def test_normal_traffic_has_required_function():
    source = NORMAL_TRAFFIC.read_text(
        encoding="utf-8"
    )

    assert "def run_normal_traffic(" in source


def test_congestion_scenario_has_required_function():
    source = CONGESTION_SCENARIO.read_text(
        encoding="utf-8"
    )

    assert "def run_congestion_scenario(" in source


def test_congestion_scenario_starts_clients_before_collecting():
    source = CONGESTION_SCENARIO.read_text(
        encoding="utf-8"
    )

    start_position = source.index(
        "start_iperf_client("
    )

    communicate_position = source.index(
        '["process"].communicate()'
    )

    assert start_position < communicate_position


def test_congestion_scenario_uses_udp():
    source = CONGESTION_SCENARIO.read_text(
        encoding="utf-8"
    )

    assert '"protocol": "udp"' in source
    assert "rate_mbps" in source


def test_phase5_runner_has_required_functions():
    source = PHASE5_RUNNER.read_text(
        encoding="utf-8"
    )

    required_functions = [
        "configure_logging",
        "verify_connectivity",
        "run_phase5",
        "parse_arguments",
        "main",
    ]

    for function_name in required_functions:
        assert f"def {function_name}(" in source


def test_traffic_generator_requests_server_output():
    source = TRAFFIC_GENERATOR.read_text(
        encoding="utf-8"
    )

    assert "--get-server-output" in source


def test_traffic_generator_has_receiver_stats_function():
    source = TRAFFIC_GENERATOR.read_text(
        encoding="utf-8"
    )

    assert "def extract_receiver_udp_stats(" in source


def test_receiver_udp_stats_extraction():
    from traffic.traffic_generator import (
        extract_receiver_udp_stats,
    )

    result = {
        "server_output_json": {
            "intervals": [
                {
                    "sum": {
                        "bits_per_second": 4_900_000,
                        "sender": False,
                    }
                },
                {
                    "sum": {
                        "bits_per_second": 5_000_000,
                        "sender": False,
                    }
                },
            ],
            "end": {
                "streams": [
                    {
                        "udp": {
                            "packets": 100,
                            "lost_packets": 5,
                            "lost_percent": 5,
                            "jitter_ms": 0.2,
                            "sender": False,
                        }
                    }
                ]
            },
        }
    }

    stats = extract_receiver_udp_stats(result)

    assert stats is not None
    assert stats["throughput_mbps"] == 5.0
    assert stats["packets"] == 100
    assert stats["lost_packets"] == 5
    assert stats["loss_pct"] == 100 * 5 / 105
    assert stats["jitter_ms"] == 0.2


def test_receiver_udp_stats_requires_receiver_data():
    from traffic.traffic_generator import (
        extract_receiver_udp_stats,
    )

    result = {
        "server_output_json": {
            "end": {
                "streams": [
                    {
                        "udp": {
                            "packets": 100,
                            "lost_packets": 0,
                            "sender": True,
                        }
                    }
                ]
            }
        }
    }

    assert extract_receiver_udp_stats(result) is None


def test_receiver_udp_stats_from_server_output_text():
    from traffic.traffic_generator import (
        extract_receiver_udp_stats,
    )

    server_output = """
[  7]   0.00-1.00   sec   578 KBytes  4.74 Mbits/sec  0.048 ms  0/409 (0%)
[  7]   1.00-2.00   sec   611 KBytes  5.00 Mbits/sec  0.043 ms  0/432 (0%)
[  7]  29.00-30.00  sec   611 KBytes  5.00 Mbits/sec  0.064 ms  0/432 (0%)
[  7]  30.00-30.05  sec  31.1 KBytes  4.82 Mbits/sec  0.046 ms  0/22 (0%)
- - - - - - - - - - - - - - - - - - - - - - - - -
[  7]   0.00-30.05  sec  17.9 MBytes  4.99 Mbits/sec  0.046 ms  0/12949 (0%)  receiver
"""

    result = {
        "server_output_text": server_output,
    }

    stats = extract_receiver_udp_stats(result)

    assert stats is not None
    assert abs(stats["throughput_mbps"] - 4.99) < 0.001
    assert stats["packets"] == 12949
    assert stats["lost_packets"] == 0
    assert stats["loss_pct"] == 0.0
    assert abs(stats["jitter_ms"] - 0.046) < 0.0001
