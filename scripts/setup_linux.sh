#!/usr/bin/env bash
# =============================================================================
# setup_linux.sh
# LINUX-SIMULATION-REQUIRED
#
# Sets up the Ubuntu/WSL2 simulation machine for the AI-Driven
# Predictive Self-Healing SDN project.
#
# Usage:
#   bash scripts/setup_linux.sh
#
# Run ONLY on the personal Ubuntu/WSL2 simulation machine.
# DO NOT run on the Windows work laptop.
#
# This script will:
#   1. Update system packages
#   2. Install system-level dependencies (Mininet, OVS, iperf3)
#   3. Create a Python virtual environment
#   4. Install Python dependencies
#   5. Verify the installation
#
# The script will prompt before making system-level changes.
# It does NOT blindly overwrite existing installations.
# =============================================================================

set -euo pipefail

GREEN='\033[0;32m'
RED='\033[0;91m'
YELLOW='\033[0;93m'
NC='\033[0m'

info()    { echo -e "${GREEN}[SETUP]${NC} $1"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $1"; }
error()   { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# ── Sanity checks ─────────────────────────────────────────────────────────────
echo
echo "============================================================"
echo "  AI-Driven Predictive Self-Healing SDN — Linux Setup"
echo "  Repository: $REPO_ROOT"
echo "  Host: $(hostname)  |  $(uname -srm)"
echo "============================================================"
echo

# Verify running on Linux
if [[ "$(uname -s)" != "Linux" ]]; then
    error "This script must be run on Linux (Ubuntu/WSL2), not $(uname -s)."
fi

# Verify running as non-root (sudo used for specific commands only)
if [[ "$EUID" -eq 0 ]]; then
    warn "Running as root. Prefer running as a regular user with sudo access."
fi

# ── Step 1: System Update ─────────────────────────────────────────────────────
info "Step 1: Updating system package list..."
read -rp "  Proceed with apt-get update? [y/N] " confirm
if [[ "$confirm" =~ ^[Yy]$ ]]; then
    sudo apt-get update -y
    info "Package list updated."
else
    warn "Skipped apt-get update."
fi

# ── Step 2: System-Level Dependencies ─────────────────────────────────────────
info "Step 2: Installing system-level dependencies..."
echo
echo "  The following packages will be installed via apt-get:"
echo "    - python3, python3-pip, python3-venv, python3-dev"
echo "    - build-essential"
echo "    - mininet"
echo "    - openvswitch-switch, openvswitch-common"
echo "    - iperf3"
echo "    - iputils-ping, net-tools"
echo "    - git"
echo

read -rp "  Proceed with installation? [y/N] " confirm
if [[ "$confirm" =~ ^[Yy]$ ]]; then
    sudo apt-get install -y \
        python3 \
        python3-pip \
        python3-venv \
        python3-dev \
        build-essential \
        mininet \
        openvswitch-switch \
        openvswitch-common \
        iperf3 \
        iputils-ping \
        net-tools \
        git
    info "System packages installed."
else
    warn "Skipped system package installation."
fi

# ── Step 3: Start Open vSwitch ────────────────────────────────────────────────
info "Step 3: Starting Open vSwitch service..."
sudo service openvswitch-switch start || warn "Could not start OVS service — may need manual intervention"
sudo ovs-vsctl show && info "OVS running." || warn "OVS not responding — check service status"

# ── Step 4: Python Virtual Environment ───────────────────────────────────────
info "Step 4: Setting up Python virtual environment..."
VENV_PATH="$REPO_ROOT/.venv"

if [[ -d "$VENV_PATH" ]]; then
    warn "Virtual environment already exists at $VENV_PATH"
    read -rp "  Re-create it? This will delete the existing .venv [y/N] " confirm
    if [[ "$confirm" =~ ^[Yy]$ ]]; then
        rm -rf "$VENV_PATH"
        python3 -m venv "$VENV_PATH"
        info "Virtual environment re-created."
    else
        info "Using existing virtual environment."
    fi
else
    python3 -m venv "$VENV_PATH"
    info "Virtual environment created at $VENV_PATH"
fi

# Activate
# shellcheck source=/dev/null
source "$VENV_PATH/bin/activate"
info "Virtual environment activated."

# ── Step 5: Upgrade pip ───────────────────────────────────────────────────────
info "Step 5: Upgrading pip..."
pip install --upgrade pip

# ── Step 6: Install Python Dependencies ──────────────────────────────────────
info "Step 6: Installing Python dependencies..."

# Verify Python version — 3.10 is required for Ryu compatibility
PY_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MINOR=$(python3 -c "import sys; print(sys.version_info.minor)")
if [[ "$PY_MINOR" -gt 11 ]]; then
    warn "Python $PY_VERSION detected. Ryu 4.34 is best tested with Python 3.10."
    warn "On Ubuntu 22.04, the system default is Python 3.10."
    warn "If you are on Ubuntu 24.04+, Ryu installation may require extra steps."
    warn "See docs/ryu_compatibility.md for details."
    read -rp "  Continue anyway? [y/N] " confirm
    [[ "$confirm" =~ ^[Yy]$ ]] || { error "Aborting. Switch to Python 3.10 first."; }
fi

# Cross-platform runtime requirements first
pip install -r "$REPO_ROOT/requirements.txt"
info "Cross-platform runtime dependencies installed."

# Install eventlet FIRST, pinned to version compatible with Ryu
# DO NOT let requirements-linux.txt install ryu before eventlet
info "Installing eventlet (pinned to 0.33.3 for Ryu compatibility)..."
pip install "eventlet==0.33.3"
info "eventlet 0.33.3 installed."

# ── Step 7: Install Ryu ───────────────────────────────────────────────────────
info "Step 7: Installing Ryu SDN controller..."

# Upgrade setuptools/pip first to avoid pbr/metadata errors
pip install --upgrade setuptools pip

# Try faucetsdn fork first (better Python 3.x compatibility)
info "Attempting Ryu install from faucetsdn git source..."
if pip install git+https://github.com/faucetsdn/ryu.git; then
    info "Ryu installed from faucetsdn git source."
else
    warn "faucetsdn git install failed. Trying PyPI ryu==4.34..."
    if pip install ryu==4.34; then
        info "Ryu 4.34 installed from PyPI."
    else
        error "Ryu installation failed. See docs/ryu_compatibility.md for manual steps."
    fi
fi

# Verify Ryu is importable
if python3 -c "from ryu.base import app_manager" &>/dev/null; then
    info "Ryu import verification: PASSED"
else
    warn "Ryu import verification: FAILED — check docs/ryu_compatibility.md"
fi

# ── Step 8: Set Script Permissions ────────────────────────────────────────────
info "Step 8: Setting script permissions..."
chmod +x "$REPO_ROOT/scripts/verify_linux_environment.sh"
chmod +x "$REPO_ROOT/scripts/run_demo.sh"
chmod +x "$REPO_ROOT/scripts/cleanup.sh"
info "Script permissions set."

# ── Step 9: Verify Installation ───────────────────────────────────────────────
info "Step 9: Running environment verification..."
echo
bash "$REPO_ROOT/scripts/verify_linux_environment.sh" || \
    warn "Some checks failed — review output above"

# ── Done ──────────────────────────────────────────────────────────────────────
echo
echo "============================================================"
info "Setup complete."
echo
echo "  To activate the virtual environment in future sessions:"
echo "    source .venv/bin/activate"
echo
echo "  To verify the environment at any time:"
echo "    bash scripts/verify_linux_environment.sh"
echo
echo "  To run the demo:"
echo "    bash scripts/run_demo.sh"
echo "============================================================"
echo
