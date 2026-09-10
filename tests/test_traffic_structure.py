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
