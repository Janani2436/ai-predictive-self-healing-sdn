"""
tests/test_monitoring_structure.py
WINDOWS-COMPATIBLE

Static validation tests for the Phase 6 monitoring controller.

These tests do not import Ryu or require Mininet/OVS. They validate
the source structure and the required monitoring logic.
"""

import ast
import os

import pytest


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MONITORING_CONTROLLER = os.path.join(
    REPO_ROOT, "monitoring", "monitoring_controller.py"
)


def _read_source() -> str:
    with open(MONITORING_CONTROLLER, "r", encoding="utf-8") as fh:
        return fh.read()


def _parse_source() -> ast.Module:
    source = _read_source()
    try:
        return ast.parse(source)
    except SyntaxError as exc:
        pytest.fail(f"SyntaxError in monitoring_controller.py: {exc}")


def _get_class_methods(class_name: str) -> list[str]:
    tree = _parse_source()

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return [
                item.name
                for item in node.body
                if isinstance(item, ast.FunctionDef)
            ]

    return []


class TestMonitoringControllerFile:
    def test_file_exists(self):
        assert os.path.isfile(MONITORING_CONTROLLER)

    def test_valid_python_syntax(self):
        _parse_source()

    def test_linux_simulation_required_marker(self):
        assert "LINUX-SIMULATION-REQUIRED" in _read_source()

    def test_openflow_13_declared(self):
        source = _read_source()
        assert "ofproto_v1_3" in source
        assert "OFP_VERSIONS" in source

    def test_ryu_components_present(self):
        source = _read_source()
        assert "app_manager" in source
        assert "ofp_event" in source
        assert "set_ev_cls" in source

    def test_monitoring_log_prefixes_present(self):
        source = _read_source()
        assert "[RYU]" in source
        assert "[OPENFLOW]" in source
        assert "[MONITOR]" in source

    def test_csv_support_present(self):
        source = _read_source()
        assert "csv" in source
        assert "port_stats.csv" in source


class TestMonitoringControllerClass:
    def test_class_exists(self):
        tree = _parse_source()
        class_names = [
            node.name
            for node in ast.walk(tree)
            if isinstance(node, ast.ClassDef)
        ]
        assert "MonitoringController" in class_names

    def test_required_methods_present(self):
        methods = _get_class_methods("MonitoringController")

        required = [
            "__init__",
            "_prepare_output_file",
            "state_change_handler",
            "_monitor",
            "_request_port_stats",
            "port_stats_reply_handler",
            "_append_rows",
        ]

        for method in required:
            assert method in methods, f"Missing method: {method}"

    def test_polling_logic_present(self):
        source = _read_source()
        assert "hub.spawn" in source
        assert "hub.sleep" in source
        assert "_request_port_stats" in source

    def test_port_stats_request_present(self):
        source = _read_source()
        assert "OFPPortStatsRequest" in source
        assert "OFPP_ANY" in source

    def test_real_byte_delta_calculation_present(self):
        source = _read_source()
        assert "stat.tx_bytes" in source
        assert "stat.rx_bytes" in source
        assert "tx_delta" in source
        assert "rx_delta" in source
        assert "previous_stats" in source

    def test_throughput_calculation_present(self):
        source = _read_source()
        assert "tx_mbps" in source
        assert "rx_mbps" in source
        assert "1_000_000" in source

    def test_utilization_calculation_present(self):
        source = _read_source()
        assert "utilization_pct" in source
        assert "link_capacity_mbps" in source

    def test_special_openflow_ports_are_skipped(self):
        source = _read_source()
        assert "OFPP_MAX" in source

    def test_required_csv_fields_present(self):
        source = _read_source()

        required_fields = [
            '"timestamp"',
            '"switch"',
            '"port"',
            '"tx_bytes"',
            '"rx_bytes"',
            '"tx_throughput_mbps"',
            '"rx_throughput_mbps"',
            '"utilization_pct"',
        ]

        for field in required_fields:
            assert field in source, f"Missing CSV field: {field}"

    def test_no_fabricated_end_to_end_metrics(self):
        source = _read_source()

        forbidden_assignments = [
            "delay_ms =",
            "packet_loss_pct =",
            "loss_pct =",
        ]

        for assignment in forbidden_assignments:
            assert assignment not in source

        assert "does not fabricate end-to-end delay or packet loss" in source
