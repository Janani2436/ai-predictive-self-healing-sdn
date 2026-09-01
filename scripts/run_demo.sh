#!/usr/bin/env bash
# =============================================================================
# run_demo.sh
# LINUX-SIMULATION-REQUIRED
#
# End-to-end demo script for AI-Driven Predictive Self-Healing SDN.
#
# Usage:
#   bash scripts/run_demo.sh [--mode full|fallback]
#
# Modes:
#   full      — complete integrated demo (controller + topology + ML + rerouting)
#   fallback  — individual component demos (standalone ML + path optimizer)
#
# Run ONLY on the personal Ubuntu/WSL2 simulation machine.
# DO NOT run on the Windows work laptop.
#
# STATUS: PLANNED — not yet executed.
# Commands will be verified and updated after first successful run on Ubuntu.
# =============================================================================

set -euo pipefail

GREEN='\033[0;32m'
RED='\033[0;91m'
YELLOW='\033[0;93m'
CYAN='\033[0;96m'
NC='\033[0m'

info()    { echo -e "${GREEN}[DEMO]${NC}  $1"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $1"; }
error()   { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }
step()    { echo; echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; echo -e "${CYAN}  STEP $1${NC}"; echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; }

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODE="${1:---mode}"
MODE_VAL="${2:-full}"
if [[ "$MODE" == "--mode" ]]; then
    DEMO_MODE="$MODE_VAL"
else
    DEMO_MODE="full"
fi

# ── Sanity checks ─────────────────────────────────────────────────────────────
if [[ "$(uname -s)" != "Linux" ]]; then
    error "This script must be run on Linux (Ubuntu/WSL2). Current OS: $(uname -s)"
fi

echo
echo "============================================================"
echo "  AI-Driven Predictive Self-Healing SDN — Demo"
echo "  Mode: $DEMO_MODE"
echo "  Repository: $REPO_ROOT"
echo "============================================================"
echo
warn "STATUS: This demo script is PLANNED and not yet fully verified."
warn "        Commands reflect intended behaviour pending Linux execution."
echo

# Activate virtual environment
if [[ -f "$REPO_ROOT/.venv/bin/activate" ]]; then
    # shellcheck source=/dev/null
    source "$REPO_ROOT/.venv/bin/activate"
    info "Virtual environment activated."
else
    error ".venv not found. Run bash scripts/setup_linux.sh first."
fi

# ── Step 1: Environment Check ─────────────────────────────────────────────────
step "1 — Environment Check"
bash "$REPO_ROOT/scripts/verify_linux_environment.sh" || {
    error "Environment check failed. Fix issues before running demo."
}

# ── Step 2: Start OVS ─────────────────────────────────────────────────────────
step "2 — Start Open vSwitch"
sudo service openvswitch-switch start
info "OVS started."

# ── Step 3: Start Ryu Controller ──────────────────────────────────────────────
step "3 — Start Ryu Controller"
info "Starting Ryu monitoring controller in background..."
mkdir -p "$REPO_ROOT/logs"
ryu-manager "$REPO_ROOT/controller/monitoring_controller.py" \
    --observe-links \
    --ofp-tcp-listen-port 6633 \
    &> "$REPO_ROOT/logs/ryu_demo.log" &
RYU_PID=$!
info "Ryu started (PID $RYU_PID). Log: logs/ryu_demo.log"
sleep 3  # Allow Ryu to initialise

# ── Step 4: Start Campus Topology ─────────────────────────────────────────────
step "4 — Start Campus Topology"
info "Starting campus topology in background..."
sudo python "$REPO_ROOT/topology/campus_topology.py" \
    &> "$REPO_ROOT/logs/mininet_demo.log" &
MN_PID=$!
info "Mininet started (PID $MN_PID). Log: logs/mininet_demo.log"
sleep 5  # Allow topology to initialise and connect to controller

# ── Step 5: Connectivity Test ─────────────────────────────────────────────────
step "5 — Connectivity Test (pingall)"
info "Running pingall via Mininet Python API..."
# NOTE: When campus_topology.py runs in interactive mode, use Mininet CLI.
# For automated demo, campus_topology.py should support --pingall flag.
# This step requires the topology script to expose a pingall option.
warn "Automated pingall requires topology/campus_topology.py --pingall flag (PLANNED)"

# ── Step 6: Normal Traffic ────────────────────────────────────────────────────
step "6 — Normal Traffic Baseline (30 seconds)"
info "Generating background traffic..."
warn "Traffic generation requires Mininet hosts to be running (PLANNED)"
# Intended command:
#   mn_exec H1 iperf3 -c 10.0.0.4 -b 10M -t 30

sleep 5

# ── Step 7: Congestion Demo ───────────────────────────────────────────────────
step "7 — Congestion Scenario"
info "Injecting high-bandwidth traffic..."
warn "Congestion injection requires live Mininet session (PLANNED)"
# Intended command:
#   mn_exec H1 iperf3 -c 10.0.0.4 -b 95M -t 60 &

sleep 5

# ── Step 8: ML Prediction (standalone) ───────────────────────────────────────
step "8 — ML Prediction (Standalone)"
info "Running prediction on sample congestion feature vector..."
python "$REPO_ROOT/ml/predict.py" \
    --utilization 91 \
    --delay 48 \
    --packet_loss 3.2 \
    --traffic_rate 85 \
    --queue_length 18 \
    || warn "predict.py not yet implemented or model not trained"

# ── Step 9: Path Optimizer (standalone) ──────────────────────────────────────
step "9 — Path Optimizer (Standalone)"
info "Running path optimizer demo..."
python "$REPO_ROOT/routing/path_optimizer.py" --demo \
    || warn "path_optimizer.py --demo not yet implemented"

# ── Step 10: Link Failure Demo ────────────────────────────────────────────────
step "10 — Link Failure and Recovery"
warn "Link failure simulation requires live Mininet session (PLANNED)"
# Intended Mininet CLI commands:
#   mininet> link D1 C1 down
#   (observe recovery in Ryu logs)
#   mininet> link D1 C1 up

# ── Step 11: Results ──────────────────────────────────────────────────────────
step "11 — Results"
RESULTS_DIR="$REPO_ROOT/experiments/results"
if ls "$RESULTS_DIR"/*.csv &>/dev/null 2>&1; then
    info "Latest experiment results:"
    ls -lt "$RESULTS_DIR"/*.csv | head -5
else
    warn "No experiment results yet. Run experiment scripts on Ubuntu."
fi

# ── Step 12: Cleanup ──────────────────────────────────────────────────────────
step "12 — Cleanup"
info "Stopping Ryu and Mininet..."
kill "$RYU_PID" 2>/dev/null || true
kill "$MN_PID" 2>/dev/null || true
bash "$REPO_ROOT/scripts/cleanup.sh"

echo
echo "============================================================"
info "Demo complete."
echo
echo "  Ryu log:     logs/ryu_demo.log"
echo "  Mininet log: logs/mininet_demo.log"
echo "  Results:     experiments/results/"
echo "============================================================"
echo
