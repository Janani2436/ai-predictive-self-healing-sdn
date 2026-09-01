#!/usr/bin/env bash
# =============================================================================
# cleanup.sh
# LINUX-SIMULATION-REQUIRED
#
# Safely cleans up Mininet processes, OVS state, and temporary files
# after experiments or after a crashed session.
#
# Usage:
#   bash scripts/cleanup.sh [--full]
#
# Options:
#   (none)  — clean Mininet processes and OVS flows only
#   --full  — also remove temporary log files and experiment temp dirs
#
# This script will NOT delete:
#   - dataset/raw/*.csv  (experiment data)
#   - ml/models/*.joblib (trained models)
#   - Any committed source files
#
# Run ONLY on the personal Ubuntu/WSL2 simulation machine.
# DO NOT run on the Windows work laptop.
# =============================================================================

set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[0;93m'
RED='\033[0;91m'
NC='\033[0m'

info()  { echo -e "${GREEN}[CLEANUP]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}    $1"; }
error() { echo -e "${RED}[ERROR]${NC}   $1"; }

FULL_CLEAN=false
if [[ "${1:-}" == "--full" ]]; then
    FULL_CLEAN=true
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo
echo "============================================================"
echo "  AI-Driven Predictive Self-Healing SDN — Cleanup"
if $FULL_CLEAN; then
    echo "  Mode: FULL"
else
    echo "  Mode: Standard"
fi
echo "============================================================"
echo

# ── 1. Mininet cleanup ────────────────────────────────────────────────────────
info "Cleaning up Mininet processes..."
if command -v mn &>/dev/null; then
    sudo mn --clean 2>/dev/null && info "mn --clean completed." || \
        warn "mn --clean returned non-zero (may be no active topology)"
else
    warn "mn not found — skipping Mininet cleanup"
fi

# ── 2. Kill stale ryu-manager processes ───────────────────────────────────────
info "Checking for stale ryu-manager processes..."
if pgrep -f "ryu-manager" &>/dev/null; then
    pkill -f "ryu-manager" && info "ryu-manager processes terminated." || \
        warn "Could not terminate ryu-manager (may already be stopped)"
else
    info "No ryu-manager processes found."
fi

# ── 3. Kill stale iperf3 server processes ─────────────────────────────────────
info "Checking for stale iperf3 server processes..."
if pgrep -f "iperf3" &>/dev/null; then
    pkill -f "iperf3" && info "iperf3 processes terminated." || \
        warn "Could not terminate iperf3"
else
    info "No iperf3 processes found."
fi

# ── 4. Release OpenFlow port ──────────────────────────────────────────────────
CONTROLLER_PORT=${CONTROLLER_PORT:-6633}
info "Releasing port $CONTROLLER_PORT if occupied..."
if command -v fuser &>/dev/null; then
    sudo fuser -k "${CONTROLLER_PORT}/tcp" 2>/dev/null && \
        info "Port $CONTROLLER_PORT released." || \
        info "Port $CONTROLLER_PORT was not in use."
else
    warn "fuser not available — skipping port release"
fi

# ── 5. Clean OVS bridges (optional — only if Mininet left orphans) ────────────
info "Checking for orphaned OVS bridges..."
if command -v ovs-vsctl &>/dev/null; then
    BRIDGES=$(sudo ovs-vsctl list-br 2>/dev/null || true)
    if [[ -n "$BRIDGES" ]]; then
        warn "Found OVS bridges: $BRIDGES"
        read -rp "  Delete all orphaned OVS bridges? [y/N] " confirm
        if [[ "$confirm" =~ ^[Yy]$ ]]; then
            while IFS= read -r bridge; do
                sudo ovs-vsctl del-br "$bridge" 2>/dev/null && \
                    info "Deleted bridge: $bridge" || \
                    warn "Could not delete bridge: $bridge"
            done <<< "$BRIDGES"
        else
            warn "Skipped OVS bridge deletion."
        fi
    else
        info "No orphaned OVS bridges found."
    fi
else
    warn "ovs-vsctl not available — skipping OVS bridge check"
fi

# ── 6. Leftover network interfaces ────────────────────────────────────────────
info "Checking for leftover Mininet virtual interfaces..."
LEFTOVER=$(ip link show 2>/dev/null | grep -E "s[0-9]+-eth[0-9]+" | awk '{print $2}' | tr -d ':' || true)
if [[ -n "$LEFTOVER" ]]; then
    warn "Found leftover interfaces: $(echo "$LEFTOVER" | tr '\n' ' ')"
    for intf in $LEFTOVER; do
        sudo ip link delete "$intf" 2>/dev/null && \
            info "Deleted interface: $intf" || \
            warn "Could not delete: $intf"
    done
else
    info "No leftover virtual interfaces found."
fi

# ── 7. Full clean: remove runtime logs and temp files ────────────────────────
if $FULL_CLEAN; then
    info "Full clean: removing runtime logs..."
    LOG_DIR="$REPO_ROOT/logs"
    if [[ -d "$LOG_DIR" ]]; then
        find "$LOG_DIR" -name "*.log" -type f -delete
        info "Log files removed from $LOG_DIR"
    fi

    info "Full clean: removing Python cache..."
    find "$REPO_ROOT" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find "$REPO_ROOT" -name "*.pyc" -delete 2>/dev/null || true
    info "Python cache cleaned."
fi

# ── Done ──────────────────────────────────────────────────────────────────────
echo
echo "============================================================"
info "Cleanup complete."
echo
echo "  Dataset files in dataset/raw/ were NOT deleted."
echo "  Trained models in ml/models/ were NOT deleted."
echo "  Experiment results in experiments/results/ were NOT deleted."
if $FULL_CLEAN; then
    echo "  Runtime logs were deleted (--full mode)."
fi
echo "============================================================"
echo
