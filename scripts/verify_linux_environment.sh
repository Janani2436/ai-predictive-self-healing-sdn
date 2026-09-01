#!/usr/bin/env bash
# =============================================================================
# verify_linux_environment.sh
# LINUX-SIMULATION-REQUIRED
#
# Verifies that the Ubuntu/WSL2 simulation machine has all required
# components installed and operational.
#
# Usage:
#   bash scripts/verify_linux_environment.sh
#
# Run ONLY on the personal Ubuntu/WSL2 simulation machine.
# DO NOT run on the Windows work laptop.
#
# Exit codes:
#   0 — all checks PASS
#   1 — one or more checks FAILED
# =============================================================================

set -euo pipefail

# ── Colour output ─────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
RED='\033[0;91m'
YELLOW='\033[0;93m'
CYAN='\033[0;96m'
NC='\033[0m'  # no colour

PASS_COUNT=0
FAIL_COUNT=0
WARN_COUNT=0

pass()    { echo -e "  ${GREEN}[PASS]${NC}    $1"; ((PASS_COUNT++)); }
fail()    { echo -e "  ${RED}[FAIL]${NC}    $1"; ((FAIL_COUNT++)); }
warn()    { echo -e "  ${YELLOW}[WARN]${NC}    $1"; ((WARN_COUNT++)); }
section() { echo; echo "──────────────────────────────────────────────────────────"; echo "  $1"; echo "──────────────────────────────────────────────────────────"; }

# ── Helper: check a command exists ────────────────────────────────────────────
check_command() {
    local cmd="$1"
    local label="${2:-$1}"
    if command -v "$cmd" &>/dev/null; then
        local version
        version=$("$cmd" --version 2>&1 | head -1 || true)
        pass "$label  ($version)"
        return 0
    else
        fail "$label — not found"
        return 1
    fi
}

# ── Helper: check a Python package ────────────────────────────────────────────
check_python_pkg() {
    local pkg="$1"
    local import_name="${2:-$1}"
    if python3 -c "import $import_name; v = getattr($import_name,'__version__','unknown'); print(v)" &>/dev/null; then
        local version
        version=$(python3 -c "import $import_name; print(getattr($import_name,'__version__','unknown'))" 2>/dev/null)
        pass "Python: $pkg  $version"
        return 0
    else
        fail "Python: $pkg — not installed"
        return 1
    fi
}

# =============================================================================
# CHECKS BEGIN
# =============================================================================

echo
echo "============================================================"
echo "  AI-Driven Predictive Self-Healing SDN"
echo "  Linux Simulation Environment Verification"
echo "  Host: $(hostname)  |  $(uname -srm)"
echo "============================================================"

# ── Operating System ──────────────────────────────────────────────────────────
section "Operating System"
if grep -qi ubuntu /etc/os-release 2>/dev/null; then
    DISTRO=$(grep PRETTY_NAME /etc/os-release | cut -d= -f2 | tr -d '"')
    pass "OS: $DISTRO"
else
    warn "OS: Not Ubuntu — some steps may differ"
fi

# WSL2 check
if grep -qi microsoft /proc/version 2>/dev/null; then
    pass "Running inside WSL2"
else
    warn "Not detected as WSL2 — may still work on native Ubuntu"
fi

# ── System Tools ──────────────────────────────────────────────────────────────
section "System Tools"
check_command python3 "Python 3"
check_command pip3 "pip3"
check_command git "Git"

# Python version check
PY_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)
if [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -ge 10 ]; then
    pass "Python version $PY_VERSION (>= 3.10 required)"
else
    fail "Python version $PY_VERSION — need 3.10+"
fi

# ── Mininet ───────────────────────────────────────────────────────────────────
section "Mininet"
if command -v mn &>/dev/null; then
    MN_VERSION=$(mn --version 2>&1 | head -1 || true)
    pass "Mininet: $MN_VERSION"
else
    fail "Mininet — not found  (sudo apt-get install mininet)"
fi

# Check Mininet Python module
if python3 -c "from mininet.net import Mininet" &>/dev/null; then
    pass "Mininet Python module importable"
else
    fail "Mininet Python module not importable"
fi

# ── Open vSwitch ──────────────────────────────────────────────────────────────
section "Open vSwitch (OVS)"
check_command ovs-vsctl "ovs-vsctl"
check_command ovs-ofctl "ovs-ofctl"

# Check OVS service is running
if sudo service openvswitch-switch status &>/dev/null || \
   systemctl is-active --quiet openvswitch-switch 2>/dev/null; then
    pass "OVS service: running"
else
    warn "OVS service: not running  (sudo service openvswitch-switch start)"
fi

# ── Ryu SDN Controller ────────────────────────────────────────────────────────
section "Ryu SDN Controller"
if command -v ryu-manager &>/dev/null; then
    RYU_VERSION=$(python3 -c "import ryu; print(ryu.__version__)" 2>/dev/null || echo "version unknown")
    pass "ryu-manager found  (ryu $RYU_VERSION)"
else
    fail "ryu-manager — not found  (pip install ryu)"
fi

if python3 -c "from ryu.base import app_manager" &>/dev/null; then
    pass "Ryu Python module importable"
else
    fail "Ryu Python module not importable"
fi

if python3 -c "from ryu.ofproto import ofproto_v1_3" &>/dev/null; then
    pass "OpenFlow 1.3 module available"
else
    fail "OpenFlow 1.3 module not available"
fi

# ── Traffic Tools ─────────────────────────────────────────────────────────────
section "Traffic Generation Tools"
check_command iperf3 "iperf3"
check_command ping "ping (ICMP)"

# ── Cross-Platform Python Packages ────────────────────────────────────────────
section "Python Packages (requirements.txt)"
check_python_pkg "numpy"
check_python_pkg "pandas"
check_python_pkg "scikit-learn" "sklearn"
check_python_pkg "joblib"
check_python_pkg "networkx"
check_python_pkg "matplotlib"
check_python_pkg "python-dotenv" "dotenv"
check_python_pkg "PyYAML" "yaml"
check_python_pkg "tqdm"

# ── Linux-specific Python Packages ────────────────────────────────────────────
section "Linux-Specific Python Packages (requirements-linux.txt)"
check_python_pkg "ryu"

# Check eventlet version specifically — wrong version breaks Ryu at startup
REQUIRED_EVENTLET="0.33.3"
if python3 -c "import eventlet; print(eventlet.__version__)" &>/dev/null; then
    INSTALLED_EVENTLET=$(python3 -c "import eventlet; print(eventlet.__version__)" 2>/dev/null)
    if [[ "$INSTALLED_EVENTLET" == "$REQUIRED_EVENTLET" ]]; then
        pass "eventlet  $INSTALLED_EVENTLET  (correct pinned version)"
    else
        warn "eventlet  $INSTALLED_EVENTLET  (expected $REQUIRED_EVENTLET — wrong version may break Ryu)"
        warn "Fix: pip install \"eventlet==$REQUIRED_EVENTLET\""
    fi
else
    fail "eventlet — not installed  (pip install \"eventlet==$REQUIRED_EVENTLET\")"
fi

# ── OpenFlow Connectivity (basic port check) ──────────────────────────────────
section "OpenFlow Port (6633)"
CONTROLLER_PORT=${CONTROLLER_PORT:-6633}
if ss -tlnp 2>/dev/null | grep -q ":${CONTROLLER_PORT}"; then
    pass "Port ${CONTROLLER_PORT}: something is listening (controller may be running)"
else
    warn "Port ${CONTROLLER_PORT}: nothing listening yet (start Ryu before this check)"
fi

# =============================================================================
# SUMMARY
# =============================================================================

echo
echo "============================================================"
echo "  SUMMARY"
echo "  PASS:    $PASS_COUNT"
echo -e "  ${RED}FAIL:    $FAIL_COUNT${NC}"
echo -e "  ${YELLOW}WARN:    $WARN_COUNT${NC}"
echo "============================================================"

if [ "$FAIL_COUNT" -gt 0 ]; then
    echo -e "  ${RED}RESULT: $FAIL_COUNT check(s) FAILED.${NC}"
    echo "  Run  bash scripts/setup_linux.sh  to install missing components."
    echo "============================================================"
    echo
    exit 1
else
    echo -e "  ${GREEN}RESULT: All required checks PASSED.${NC}"
    if [ "$WARN_COUNT" -gt 0 ]; then
        echo "  ($WARN_COUNT warning(s) — review above)"
    fi
    echo "============================================================"
    echo
    exit 0
fi
