"""
tests/test_topology_structure.py
WINDOWS-COMPATIBLE

Tests that can be executed on the Windows development machine without
Mininet, OVS, or any Linux networking dependency.

What these tests verify:
    - topology_utils.py is syntactically correct and importable on Windows
    - Configuration loading (load_config) works and returns sensible defaults
    - Controller config extraction (get_controller_config) works correctly
    - IP address formatting (format_host_ip) works correctly
    - Link parameter helper (make_link_params) returns the right structure
    - simple_topology.py is syntactically correct (AST parse)
    - SimpleTopology class can be instantiated without calling build()
      (build() would immediately fail on Windows due to missing Mininet)

What these tests do NOT verify (LINUX-SIMULATION-REQUIRED):
    - Actual Mininet network creation
    - OVS switch configuration
    - OpenFlow 1.3 handshake
    - Host connectivity (pingAll)
    - Any live networking behaviour

SYNTHETIC-DATA / WINDOWS-DEV-TESTED
"""

import ast
import os
import sys
import textwrap
import pytest

# Ensure the repo root is on the path so imports work from the test runner
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


# ---------------------------------------------------------------------------
# topology_utils.py — importability and pure-Python functions
# ---------------------------------------------------------------------------

class TestTopologyUtilsImport:
    """Verify topology_utils can be imported on Windows."""

    def test_import_topology_utils(self):
        """topology_utils must import without Mininet present."""
        import topology.topology_utils as utils  # noqa: F401
        assert utils is not None

    def test_constants_present(self):
        """Required constants must be defined."""
        from topology.topology_utils import (
            OPENFLOW_13,
            OPENFLOW_13_PORT,
            DEFAULT_CONTROLLER_IP,
            DEFAULT_CONTROLLER_PORT,
            DEFAULT_LINK_BW_MBPS,
        )
        assert OPENFLOW_13 == "OpenFlow13"
        assert OPENFLOW_13_PORT == 6633
        assert DEFAULT_CONTROLLER_IP == "127.0.0.1"
        assert DEFAULT_CONTROLLER_PORT == 6633
        assert DEFAULT_LINK_BW_MBPS == 100


class TestLoadConfig:
    """Tests for load_config() — WINDOWS-COMPATIBLE."""

    def test_load_config_missing_file_returns_defaults(self):
        """Missing config file should return default values without raising."""
        from topology.topology_utils import load_config
        config = load_config("nonexistent_config_file.yaml")
        assert isinstance(config, dict)
        assert "controller" in config
        assert "monitoring" in config

    def test_load_config_default_controller_ip(self):
        """Default controller IP must be 127.0.0.1."""
        from topology.topology_utils import load_config
        config = load_config("nonexistent_config_file.yaml")
        assert config["controller"]["host"] == "127.0.0.1"

    def test_load_config_default_controller_port(self):
        """Default controller port must be 6633."""
        from topology.topology_utils import load_config
        config = load_config("nonexistent_config_file.yaml")
        assert config["controller"]["port"] == 6633

    def test_load_config_from_example_file(self, tmp_path):
        """load_config should parse a valid YAML file correctly."""
        import yaml
        from topology.topology_utils import load_config

        cfg_file = tmp_path / "config.yaml"
        cfg_data = {
            "controller": {"host": "192.168.1.10", "port": 6654},
            "monitoring": {"poll_interval_seconds": 10},
        }
        cfg_file.write_text(yaml.dump(cfg_data), encoding="utf-8")

        config = load_config(str(cfg_file))
        assert config["controller"]["host"] == "192.168.1.10"
        assert config["controller"]["port"] == 6654
        assert config["monitoring"]["poll_interval_seconds"] == 10

    def test_load_config_malformed_yaml_returns_defaults(self, tmp_path):
        """Malformed YAML should fall back to defaults without raising."""
        from topology.topology_utils import load_config

        cfg_file = tmp_path / "bad.yaml"
        cfg_file.write_text("{{{{ not valid yaml", encoding="utf-8")
        config = load_config(str(cfg_file))
        assert isinstance(config, dict)
        assert "controller" in config


class TestGetControllerConfig:
    """Tests for get_controller_config() — WINDOWS-COMPATIBLE."""

    def test_extracts_host_and_port(self):
        """Should extract host and port from config dict."""
        from topology.topology_utils import get_controller_config
        config = {"controller": {"host": "10.0.0.1", "port": 6700}}
        host, port = get_controller_config(config)
        assert host == "10.0.0.1"
        assert port == 6700

    def test_returns_strings_and_ints(self):
        """Host must be str, port must be int."""
        from topology.topology_utils import get_controller_config
        config = {"controller": {"host": "127.0.0.1", "port": "6633"}}
        host, port = get_controller_config(config)
        assert isinstance(host, str)
        assert isinstance(port, int)

    def test_defaults_when_key_missing(self):
        """Missing controller key should fall back to defaults."""
        from topology.topology_utils import get_controller_config, DEFAULT_CONTROLLER_IP, DEFAULT_CONTROLLER_PORT
        host, port = get_controller_config({})
        assert host == DEFAULT_CONTROLLER_IP
        assert port == DEFAULT_CONTROLLER_PORT


class TestFormatHostIP:
    """Tests for format_host_ip() — WINDOWS-COMPATIBLE."""

    def test_standard_host_ip(self):
        """Host 1 on default subnet should be 10.0.0.1/24."""
        from topology.topology_utils import format_host_ip
        assert format_host_ip(1) == "10.0.0.1/24"

    def test_host_2_ip(self):
        """Host 2 on default subnet should be 10.0.0.2/24."""
        from topology.topology_utils import format_host_ip
        assert format_host_ip(2) == "10.0.0.2/24"

    def test_custom_subnet(self):
        """Should work with a custom subnet prefix."""
        from topology.topology_utils import format_host_ip
        assert format_host_ip(5, subnet="192.168.10") == "192.168.10.5/24"

    def test_host_number_boundary_low(self):
        """Host number 1 is valid."""
        from topology.topology_utils import format_host_ip
        assert format_host_ip(1).endswith("/24")

    def test_host_number_boundary_high(self):
        """Host number 254 is valid."""
        from topology.topology_utils import format_host_ip
        assert format_host_ip(254).endswith("/24")

    def test_host_number_zero_raises(self):
        """Host number 0 is invalid and must raise ValueError."""
        from topology.topology_utils import format_host_ip
        with pytest.raises(ValueError):
            format_host_ip(0)

    def test_host_number_255_raises(self):
        """Host number 255 is invalid and must raise ValueError."""
        from topology.topology_utils import format_host_ip
        with pytest.raises(ValueError):
            format_host_ip(255)


class TestMakeLinkParams:
    """Tests for make_link_params() — WINDOWS-COMPATIBLE."""

    def test_returns_dict(self):
        """make_link_params must return a dict."""
        from topology.topology_utils import make_link_params
        params = make_link_params()
        assert isinstance(params, dict)

    def test_default_bandwidth(self):
        """Default bandwidth should be 100 Mbps."""
        from topology.topology_utils import make_link_params, DEFAULT_LINK_BW_MBPS
        params = make_link_params()
        assert params["bw"] == DEFAULT_LINK_BW_MBPS

    def test_custom_bandwidth(self):
        """Custom bandwidth should be reflected in returned dict."""
        from topology.topology_utils import make_link_params
        params = make_link_params(bw_mbps=50)
        assert params["bw"] == 50

    def test_delay_key_present(self):
        """Delay key must be in returned dict."""
        from topology.topology_utils import make_link_params
        params = make_link_params(delay_ms="5ms")
        assert params["delay"] == "5ms"

    def test_loss_key_present(self):
        """Loss key must be in returned dict."""
        from topology.topology_utils import make_link_params
        params = make_link_params(loss_pct=1.5)
        assert params["loss"] == 1.5

    def test_all_required_keys_present(self):
        """All four Mininet TCLink keys must be present."""
        from topology.topology_utils import make_link_params
        params = make_link_params()
        assert "bw" in params
        assert "delay" in params
        assert "loss" in params
        assert "max_queue_size" in params


# ---------------------------------------------------------------------------
# simple_topology.py — syntax and structure (no Mininet execution)
# ---------------------------------------------------------------------------

class TestSimpleTopologySyntax:
    """Verify simple_topology.py is syntactically valid Python."""

    def _get_source_path(self) -> str:
        return os.path.join(REPO_ROOT, "topology", "simple_topology.py")

    def test_file_exists(self):
        """simple_topology.py must exist."""
        assert os.path.isfile(self._get_source_path()), \
            "topology/simple_topology.py not found"

    def test_valid_python_syntax(self):
        """simple_topology.py must parse without SyntaxError."""
        with open(self._get_source_path(), "r", encoding="utf-8") as fh:
            source = fh.read()
        try:
            ast.parse(source)
        except SyntaxError as exc:
            pytest.fail(f"SyntaxError in simple_topology.py: {exc}")

    def test_linux_simulation_required_comment_present(self):
        """The LINUX-SIMULATION-REQUIRED marker must appear in the file."""
        with open(self._get_source_path(), "r", encoding="utf-8") as fh:
            source = fh.read()
        assert "LINUX-SIMULATION-REQUIRED" in source, \
            "simple_topology.py must contain the LINUX-SIMULATION-REQUIRED marker"

    def test_openflow_13_referenced(self):
        """OpenFlow 1.3 must be explicitly referenced."""
        with open(self._get_source_path(), "r", encoding="utf-8") as fh:
            source = fh.read()
        assert "OpenFlow13" in source or "openflow_version" in source or "OF1.3" in source, \
            "simple_topology.py must reference OpenFlow 1.3"


class TestSimpleTopologyClass:
    """
    Test the SimpleTopology class without executing Mininet.

    build() is NOT called — doing so would require Linux/Mininet.
    Only instantiation and parameter validation are tested.
    """

    def test_import_simple_topology_module(self):
        """simple_topology module must import on Windows without Mininet."""
        import topology.simple_topology as st  # noqa: F401
        assert st is not None

    def test_simple_topology_class_exists(self):
        """SimpleTopology class must be defined in the module."""
        from topology.simple_topology import SimpleTopology
        assert SimpleTopology is not None

    def test_instantiation_with_defaults(self):
        """SimpleTopology should instantiate with default parameters."""
        from topology.simple_topology import SimpleTopology
        topo = SimpleTopology()
        assert topo.controller_ip == "127.0.0.1"
        assert topo.controller_port == 6633
        assert topo.net is None  # network not built yet

    def test_instantiation_with_custom_params(self):
        """SimpleTopology should accept custom controller IP and port."""
        from topology.simple_topology import SimpleTopology
        topo = SimpleTopology(
            controller_ip="192.168.1.5",
            controller_port=6654,
            link_bw_mbps=50,
            link_delay_ms="2ms",
        )
        assert topo.controller_ip == "192.168.1.5"
        assert topo.controller_port == 6654
        assert topo.link_bw_mbps == 50
        assert topo.link_delay_ms == "2ms"

    def test_stop_before_build_does_not_raise(self):
        """Calling stop() before build() should not raise an exception."""
        from topology.simple_topology import SimpleTopology
        topo = SimpleTopology()
        topo.stop()  # Should be a safe no-op

    def test_run_pingall_before_build_raises(self):
        """run_pingall() before build() must raise RuntimeError."""
        from topology.simple_topology import SimpleTopology
        topo = SimpleTopology()
        with pytest.raises(RuntimeError):
            topo.run_pingall()

    def test_build_raises_import_error_without_mininet(self):
        """
        build() must raise ImportError on Windows where Mininet is absent.

        This confirms the error path is correctly implemented and the code
        does not silently use a fake Mininet implementation.
        """
        from topology.simple_topology import SimpleTopology
        topo = SimpleTopology()
        with pytest.raises(ImportError) as exc_info:
            topo.build()
        assert "Mininet" in str(exc_info.value) or "mininet" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# topology_utils.py — syntax check
# ---------------------------------------------------------------------------

class TestTopologyUtilsSyntax:
    """Verify topology_utils.py is syntactically valid."""

    def test_valid_python_syntax(self):
        """topology_utils.py must parse without SyntaxError."""
        path = os.path.join(REPO_ROOT, "topology", "topology_utils.py")
        with open(path, "r", encoding="utf-8") as fh:
            source = fh.read()
        try:
            ast.parse(source)
        except SyntaxError as exc:
            pytest.fail(f"SyntaxError in topology_utils.py: {exc}")

    def test_linux_simulation_required_marker_present(self):
        """topology_utils.py must document the Linux boundary."""
        path = os.path.join(REPO_ROOT, "topology", "topology_utils.py")
        with open(path, "r", encoding="utf-8") as fh:
            source = fh.read()
        assert "LINUX-SIMULATION-REQUIRED" in source
