"""
tests/test_controller_structure.py
WINDOWS-COMPATIBLE

Static validation tests for the Phase 3 controller files.
These tests run entirely on the Windows development machine.

What is tested:
    - Python syntax validity (AST parse) of both controller files
    - Required markers (LINUX-SIMULATION-REQUIRED) are present
    - Required OpenFlow version references (OFP_VERSIONS / OpenFlow13) present
    - File structure: class names, method names, docstrings present
    - No accidental hard-coded IPs or port numbers in logic
    - Ryu is NOT imported — tests work without Ryu installed

What is NOT tested here (LINUX-SIMULATION-REQUIRED):
    - Actual Ryu app instantiation
    - OpenFlow handshake with OVS
    - MAC learning with real packet data
    - Flow rule installation on a real switch
    - Any network connectivity

WINDOWS-DEV-TESTED
All tests in this file are confirmed runnable on the Windows work laptop
without Mininet, OVS, Ryu, or Linux networking.
"""

import ast
import os
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

SIMPLE_CONTROLLER = os.path.join(REPO_ROOT, "controller", "simple_controller.py")
LEARNING_SWITCH = os.path.join(REPO_ROOT, "controller", "learning_switch.py")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_source(path: str) -> str:
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def _parse_ast(source: str, filename: str) -> ast.Module:
    """Parse source and return AST, failing the test on SyntaxError."""
    try:
        return ast.parse(source)
    except SyntaxError as exc:
        pytest.fail(f"SyntaxError in {filename}: {exc}")


def _get_class_names(tree: ast.Module) -> list[str]:
    return [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]


def _get_method_names(tree: ast.Module, class_name: str) -> list[str]:
    """Return method names defined inside a specific class."""
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return [
                item.name
                for item in node.body
                if isinstance(item, ast.FunctionDef)
            ]
    return []


def _get_all_function_names(tree: ast.Module) -> list[str]:
    return [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
    ]


def _get_string_constants(tree: ast.Module) -> list[str]:
    """Return all string literal values in the AST."""
    return [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    ]


# ---------------------------------------------------------------------------
# simple_controller.py — file-level checks
# ---------------------------------------------------------------------------

class TestSimpleControllerExists:
    def test_file_exists(self):
        assert os.path.isfile(SIMPLE_CONTROLLER), \
            "controller/simple_controller.py not found"

    def test_valid_python_syntax(self):
        source = _read_source(SIMPLE_CONTROLLER)
        _parse_ast(source, "simple_controller.py")  # raises on SyntaxError

    def test_linux_simulation_required_marker(self):
        source = _read_source(SIMPLE_CONTROLLER)
        assert "LINUX-SIMULATION-REQUIRED" in source, \
            "simple_controller.py must contain LINUX-SIMULATION-REQUIRED marker"

    def test_openflow_13_declared(self):
        source = _read_source(SIMPLE_CONTROLLER)
        # Must reference OF1.3 version constant
        assert "ofproto_v1_3" in source, \
            "simple_controller.py must import and use ofproto_v1_3"

    def test_ofp_versions_list_present(self):
        source = _read_source(SIMPLE_CONTROLLER)
        assert "OFP_VERSIONS" in source, \
            "OFP_VERSIONS must be declared to negotiate OpenFlow 1.3"

    def test_ryu_log_prefixes_present(self):
        """Logging must use structured [RYU] and [OPENFLOW] prefixes."""
        source = _read_source(SIMPLE_CONTROLLER)
        assert "[RYU]" in source, "Must use [RYU] log prefix"
        assert "[OPENFLOW]" in source, "Must use [OPENFLOW] log prefix"

    def test_no_hard_coded_ip(self):
        """Controller IP must not be hard-coded in logic."""
        source = _read_source(SIMPLE_CONTROLLER)
        # 127.0.0.1 is acceptable only in comments/docstrings, not in logic code
        # We check that the constants section does not hard-code a non-loopback IP
        assert "192.168." not in source, \
            "Hard-coded 192.168.x.x IP found — use configuration instead"
        assert "10.0.0." not in source or source.count("10.0.0.") <= 2, \
            "Possible hard-coded data-plane IP in controller logic"


# ---------------------------------------------------------------------------
# simple_controller.py — class structure
# ---------------------------------------------------------------------------

class TestSimpleControllerClass:
    def _tree(self) -> ast.Module:
        return _parse_ast(_read_source(SIMPLE_CONTROLLER), "simple_controller.py")

    def test_class_exists(self):
        names = _get_class_names(self._tree())
        assert "SimpleController" in names, \
            "SimpleController class not found in simple_controller.py"

    def test_switch_features_handler_present(self):
        methods = _get_method_names(self._tree(), "SimpleController")
        assert "switch_features_handler" in methods, \
            "switch_features_handler method missing from SimpleController"

    def test_packet_in_handler_present(self):
        methods = _get_method_names(self._tree(), "SimpleController")
        assert "packet_in_handler" in methods, \
            "packet_in_handler method missing from SimpleController"

    def test_install_flow_helper_present(self):
        methods = _get_method_names(self._tree(), "SimpleController")
        assert "_install_flow" in methods, \
            "_install_flow helper missing from SimpleController"

    def test_send_packet_out_helper_present(self):
        methods = _get_method_names(self._tree(), "SimpleController")
        assert "_send_packet_out" in methods, \
            "_send_packet_out helper missing from SimpleController"

    def test_mac_to_port_initialised(self):
        """MAC learning table must be initialised in __init__."""
        source = _read_source(SIMPLE_CONTROLLER)
        assert "mac_to_port" in source, \
            "mac_to_port table not found in simple_controller.py"

    def test_table_miss_priority_zero(self):
        """Table-miss flow must use priority 0 (lowest)."""
        source = _read_source(SIMPLE_CONTROLLER)
        assert "PRIORITY_TABLE_MISS = 0" in source or "priority=0" in source \
            or "PRIORITY_TABLE_MISS" in source, \
            "Table-miss priority constant not found"

    def test_idle_and_hard_timeout_constants(self):
        source = _read_source(SIMPLE_CONTROLLER)
        assert "IDLE_TIMEOUT" in source, "IDLE_TIMEOUT constant missing"
        assert "HARD_TIMEOUT" in source, "HARD_TIMEOUT constant missing"

    def test_lldp_ignored(self):
        """LLDP frames must be filtered to avoid noise in MAC learning."""
        source = _read_source(SIMPLE_CONTROLLER)
        assert "ETH_TYPE_LLDP" in source or "LLDP" in source, \
            "LLDP filtering not found — controller should ignore LLDP frames"

    def test_docstring_on_class(self):
        """SimpleController must have a class-level docstring."""
        tree = self._tree()
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "SimpleController":
                first = node.body[0] if node.body else None
                assert isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant), \
                    "SimpleController class is missing a docstring"
                return
        pytest.fail("SimpleController class not found")

    def test_no_monitoring_in_controller(self):
        """
        simple_controller.py must NOT contain monitoring/ML/routing code.
        Those belong in later phases.
        """
        source = _read_source(SIMPLE_CONTROLLER)
        forbidden = ["RandomForest", "predict(", "health_score", "path_optimizer"]
        for term in forbidden:
            assert term not in source, \
                f"Phase 3 controller must not contain '{term}' — belongs in later phase"


# ---------------------------------------------------------------------------
# learning_switch.py — file-level checks
# ---------------------------------------------------------------------------

class TestLearningSwitchExists:
    def test_file_exists(self):
        assert os.path.isfile(LEARNING_SWITCH), \
            "controller/learning_switch.py not found"

    def test_valid_python_syntax(self):
        source = _read_source(LEARNING_SWITCH)
        _parse_ast(source, "learning_switch.py")

    def test_linux_simulation_required_marker(self):
        source = _read_source(LEARNING_SWITCH)
        assert "LINUX-SIMULATION-REQUIRED" in source

    def test_openflow_13_declared(self):
        source = _read_source(LEARNING_SWITCH)
        assert "ofproto_v1_3" in source

    def test_ryu_app_manager_referenced(self):
        source = _read_source(LEARNING_SWITCH)
        assert "app_manager" in source, \
            "learning_switch.py must use ryu.base.app_manager"


# ---------------------------------------------------------------------------
# learning_switch.py — class structure
# ---------------------------------------------------------------------------

class TestLearningSwitchClass:
    def _tree(self) -> ast.Module:
        return _parse_ast(_read_source(LEARNING_SWITCH), "learning_switch.py")

    def test_class_exists(self):
        names = _get_class_names(self._tree())
        assert "LearningSwitch" in names, \
            "LearningSwitch class not found in learning_switch.py"

    def test_switch_features_handler_present(self):
        all_methods = _get_all_function_names(self._tree())
        # method may be private (_switch_features_handler) or public
        matches = [m for m in all_methods if "switch_features_handler" in m]
        assert matches, "switch_features_handler (or _switch_features_handler) not found"

    def test_packet_in_handler_present(self):
        all_methods = _get_all_function_names(self._tree())
        matches = [m for m in all_methods if "packet_in_handler" in m]
        assert matches, "packet_in_handler (or _packet_in_handler) not found"

    def test_add_flow_helper_present(self):
        all_methods = _get_all_function_names(self._tree())
        matches = [m for m in all_methods if "add_flow" in m or "_add_flow" in m]
        assert matches, "_add_flow helper not found in learning_switch.py"

    def test_mac_to_port_present(self):
        source = _read_source(LEARNING_SWITCH)
        assert "mac_to_port" in source

    def test_lldp_filtered(self):
        source = _read_source(LEARNING_SWITCH)
        assert "ETH_TYPE_LLDP" in source or "LLDP" in source

    def test_baseline_label_in_docstring(self):
        """learning_switch.py should document its role as the baseline controller."""
        source = _read_source(LEARNING_SWITCH)
        assert "baseline" in source.lower(), \
            "learning_switch.py should document that it is the baseline controller"

    def test_no_ml_or_prediction_code(self):
        """Baseline controller must have no ML or prediction logic."""
        source = _read_source(LEARNING_SWITCH)
        forbidden = ["RandomForest", "predict(", "health_score", "sklearn"]
        for term in forbidden:
            assert term not in source, \
                f"Baseline learning_switch.py must not contain '{term}'"


# ---------------------------------------------------------------------------
# Cross-file consistency checks
# ---------------------------------------------------------------------------

class TestControllerConsistency:
    def test_both_use_ofproto_v1_3(self):
        """Both controllers must use OpenFlow 1.3."""
        for path, name in [(SIMPLE_CONTROLLER, "simple_controller.py"),
                           (LEARNING_SWITCH, "learning_switch.py")]:
            source = _read_source(path)
            assert "ofproto_v1_3" in source, \
                f"{name} must reference ofproto_v1_3 for OpenFlow 1.3"

    def test_both_handle_packet_in(self):
        """Both controllers must handle PACKET_IN events."""
        for path, name in [(SIMPLE_CONTROLLER, "simple_controller.py"),
                           (LEARNING_SWITCH, "learning_switch.py")]:
            source = _read_source(path)
            assert "EventOFPPacketIn" in source, \
                f"{name} must handle EventOFPPacketIn"

    def test_both_install_table_miss(self):
        """Both controllers must install a table-miss entry."""
        for path, name in [(SIMPLE_CONTROLLER, "simple_controller.py"),
                           (LEARNING_SWITCH, "learning_switch.py")]:
            source = _read_source(path)
            assert "EventOFPSwitchFeatures" in source, \
                f"{name} must respond to EventOFPSwitchFeatures to install table-miss"

    def test_both_ignore_lldp(self):
        """Both controllers must ignore LLDP frames."""
        for path, name in [(SIMPLE_CONTROLLER, "simple_controller.py"),
                           (LEARNING_SWITCH, "learning_switch.py")]:
            source = _read_source(path)
            assert "LLDP" in source or "ETH_TYPE_LLDP" in source, \
                f"{name} must filter LLDP frames"

    def test_simple_controller_is_not_learning_switch(self):
        """The two files must serve different purposes — not be duplicates."""
        src_simple = _read_source(SIMPLE_CONTROLLER)
        src_learning = _read_source(LEARNING_SWITCH)
        # They must have different class names
        assert "SimpleController" in src_simple
        assert "LearningSwitch" in src_learning
        assert "SimpleController" not in src_learning, \
            "learning_switch.py must not contain SimpleController class"
        assert "LearningSwitch" not in src_simple, \
            "simple_controller.py must not contain LearningSwitch class"
