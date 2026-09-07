"""Structural tests for the redundant campus topology."""

from pathlib import Path


def test_topology_file_exists():
    assert Path("topology/campus_topology.py").exists()


def test_seven_switches_defined():
    text = Path("topology/campus_topology.py").read_text()

    for sw in ["c1", "d1", "d2", "a1", "a2", "a3", "a4"]:
        assert f'"{sw}"' in text


def test_unique_dpids_present():
    text = Path("topology/campus_topology.py").read_text()

    for i in range(1, 8):
        dpid = f'dpid="000000000000000{i}"'
        assert dpid in text


def test_redundant_distribution_link_exists():
    text = Path("topology/campus_topology.py").read_text()

    assert "self.net.addLink(d1, d2" in text


def test_rstp_enabled():
    text = Path("topology/campus_topology.py").read_text()

    assert "rstp_enable=true" in text
