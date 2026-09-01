# Setup Guide

## Overview

This project uses a two-machine development model:

- **Windows Work Laptop** — code development, unit testing, ML development
- **Personal Laptop (WSL2/Ubuntu)** — SDN emulation, actual experiments

Follow the appropriate section for each machine.

---

## Machine 1 — Windows Development Setup

### Prerequisites
- Windows 10/11 (64-bit)
- Python 3.10 or later (project uses 3.14)
- Git 2.x

### Verify Existing Tools

```powershell
python --version
git --version
pip --version
```

### Clone Repository

```powershell
git clone <your-repo-url>
cd ai-predictive-self-healing-sdn
```

### Create Virtual Environment

```powershell
python -m venv .venv
.venv\Scripts\activate
```

### Install Dependencies

```powershell
pip install -r requirements-dev.txt
```

This installs: numpy, pandas, scikit-learn, networkx, matplotlib, joblib,
PyYAML, python-dotenv, tqdm, pytest, pytest-cov, flake8, pylint, mypy,
black, isort.

### Verify Installation

```powershell
python scripts/verify_windows_environment.py
```

Expected output: PASS for all cross-platform dependencies, and
"NOT CHECKED / LINUX REQUIRED" for Mininet, OVS, Ryu, iperf3.

### Run Unit Tests

```powershell
pytest tests/ -v
```

---

## Phase 3 — Controller Code

### controller/simple_controller.py (LINUX-SIMULATION-REQUIRED)

Primary Ryu OpenFlow 1.3 controller. Implements MAC learning, table-miss
entry, flow installation, and reactive L2 forwarding.

### controller/learning_switch.py (LINUX-SIMULATION-REQUIRED)

Standalone baseline controller. Identical behaviour to simple_controller.py
at this phase, but kept separate for use as the conventional-SDN baseline
in Phase 14 experiments.

### Ryu Compatibility

See `docs/ryu_compatibility.md` for the full analysis.

**Recommended simulation environment:**
- Ubuntu 22.04 LTS (WSL2)
- Python 3.10 (system default — do NOT upgrade for SDN work)
- Ryu from `faucetsdn/ryu` git
- eventlet==0.33.3 (pinned — `requirements-linux.txt` updated)

**Critical fix:** `requirements-linux.txt` previously pinned `eventlet==0.40.0`
which breaks Ryu at startup. This has been corrected to `eventlet==0.33.3`.

### Running Phase 3 on Ubuntu

```bash
# Terminal 1 — start controller
source .venv/bin/activate
ryu-manager controller/simple_controller.py \
    --observe-links \
    --ofp-tcp-listen-port 6633

# Terminal 2 — start topology
sudo python topology/simple_topology.py

# In Mininet CLI
mininet> pingall
```

Expected Ryu output:
```
[RYU] SimpleController initialised. Waiting for switches.
[RYU] Switch connected: dpid=0000000000000001  OF version=4
[OPENFLOW] Table-miss flow installed on dpid=0000000000000001
[RYU] Learned: dpid=0000000000000001  mac=00:00:00:00:00:01 → port=1
[OPENFLOW] Flow installed: dpid=0000000000000001  00:00:00:00:00:02 → port=2
```

---

## Phase 2 — Topology Code

### simple_topology.py (LINUX-SIMULATION-REQUIRED)

`topology/simple_topology.py` implements the minimal h1-s1-h2 topology.

**On Ubuntu, run with:**
```bash
# Start Ryu controller first (separate terminal):
ryu-manager controller/simple_controller.py --ofp-tcp-listen-port 6633

# Then start the topology:
sudo python topology/simple_topology.py

# For automated connectivity test (no CLI):
sudo python topology/simple_topology.py --pingall --no-cli

# With custom controller address:
sudo python topology/simple_topology.py --controller-ip 127.0.0.1 --controller-port 6633
```

**Expected output (successful):**
```
10:00:01 INFO     topology.simple_topology — [TOPOLOGY] Building simple topology: H1 --- S1 --- H2
10:00:01 INFO     topology.simple_topology — [TOPOLOGY] Controller: 127.0.0.1:6633
10:00:02 INFO     topology.simple_topology — [TOPOLOGY] Switch s1 added
10:00:02 INFO     topology.simple_topology — [TOPOLOGY] Hosts added: h1=10.0.0.1/24  h2=10.0.0.2/24
10:00:02 INFO     topology.simple_topology — [TOPOLOGY] Links added: H1-S1-H2  bw=100Mbps  delay=1ms
10:00:03 INFO     topology.simple_topology — [TOPOLOGY] Network started.
10:00:03 INFO     topology.simple_topology — [TOPOLOGY] Switch s1 (dpid=...) configured for OpenFlow 1.3
10:00:03 INFO     topology.simple_topology — [TOPOLOGY] Simple topology ready.
mininet>
```

**pingAll expected output:**
```
mininet> pingall
*** Ping: testing ping reachability
h1 -> h2
h2 -> h1
*** Results: 0% dropped (2/2 received)
```

---

## Machine 2 — Ubuntu / WSL2 Simulation Setup

> **LINUX-SIMULATION-REQUIRED**
> These steps must be performed on the personal laptop running WSL2 + Ubuntu.
> Do NOT attempt on the Windows work laptop.

### Prerequisites
- Windows 10/11 with WSL2 enabled
- Ubuntu 20.04 or 22.04 LTS installed in WSL2
- Internet access for package installation

### Enable WSL2 (Windows host)

```powershell
# Run in PowerShell as Administrator
wsl --install
wsl --set-default-version 2
```

Restart when prompted, then install Ubuntu from the Microsoft Store.

### Enter Ubuntu

```bash
wsl
```

### Update System

```bash
sudo apt-get update && sudo apt-get upgrade -y
```

### Install System Dependencies

```bash
# Python and build tools
sudo apt-get install -y python3 python3-pip python3-venv python3-dev build-essential

# Mininet
sudo apt-get install -y mininet

# Open vSwitch
sudo apt-get install -y openvswitch-switch openvswitch-common

# Traffic tools
sudo apt-get install -y iperf3 iputils-ping net-tools

# Git
sudo apt-get install -y git
```

### Clone Repository (Ubuntu)

```bash
git clone <your-repo-url>
cd ai-predictive-self-healing-sdn
```

### Create Python Virtual Environment (Ubuntu)

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Install Python Dependencies (Ubuntu)

```bash
pip install -r requirements-linux.txt
```

This installs all cross-platform dependencies PLUS:
- ryu 4.34
- eventlet 0.40.0

### Install Ryu (if pip install fails)

Some Ubuntu versions may require installing Ryu from source:

```bash
pip install ryu==4.34
# If that fails:
git clone https://github.com/faucetsdn/ryu.git
cd ryu && pip install .
```

### Start Open vSwitch

```bash
sudo service openvswitch-switch start
# Verify:
sudo ovs-vsctl show
```

### Verify Full Environment

```bash
bash scripts/verify_linux_environment.sh
```

Expected output: PASS for all components.

### Run Automated Setup Script

Alternatively, run the full setup script:

```bash
bash scripts/setup_linux.sh
```

---

## Configuration

All configurable parameters are in `config.yaml` (root of repository).

```yaml
controller:
  host: 127.0.0.1
  port: 6633
  openflow_version: 1.3

monitoring:
  poll_interval_seconds: 5

routing:
  health_weights:
    delay: 0.4
    packet_loss: 0.35
    utilization: 0.25
  congestion_threshold_pct: 80.0
  failure_threshold_pct: 5.0  # packet loss

ml:
  model_path: ml/models/
  random_state: 42
  test_size: 0.2
```

Copy `config.yaml.example` to `config.yaml` and adjust for your environment.

---

## Python Version Compatibility

| Machine | Python Version | Status |
|---------|---------------|--------|
| Windows work laptop | 3.14.6 | Confirmed |
| Ubuntu simulation | 3.10+ recommended | Planned |

All code targets Python 3.10+ minimum for cross-machine compatibility.
