# Review Demo Guide

> **LINUX-SIMULATION-REQUIRED**
> This demo must be executed on the personal laptop running WSL2 + Ubuntu.
> All commands below are Linux/bash commands.
>
> Current status: **PLANNED — not yet executed**
> Commands will be verified and updated after first successful run.

---

## Pre-Demo Checklist

Before the review session, verify on the Ubuntu/WSL2 machine:

```bash
# 1. Environment check
bash scripts/verify_linux_environment.sh

# 2. OVS running
sudo service openvswitch-switch status

# 3. Repository up to date
git pull origin main

# 4. Virtual environment active
source .venv/bin/activate

# 5. ML model available
ls ml/models/
```

---

## Phase 3 — Controller Verification

> **LINUX-SIMULATION-REQUIRED**
> Status: Code complete (WINDOWS-DEV-TESTED). Linux execution pending.

### Step 0 — Install Ryu on Ubuntu (one-time setup)

```bash
# Ensure you are on Ubuntu 22.04 with Python 3.10
python3 --version   # must be 3.10.x

source .venv/bin/activate

# Install eventlet FIRST — pinned version required
pip install "eventlet==0.33.3"

# Install Ryu from faucetsdn git source
pip install git+https://github.com/faucetsdn/ryu.git

# Verify
python3 -c "from ryu.base import app_manager; print('Ryu OK')"
python3 -c "from ryu.ofproto import ofproto_v1_3; print('OF1.3 OK')"
```

Expected output:
```
Ryu OK
OF1.3 OK
```

If this fails, see `docs/ryu_compatibility.md` for troubleshooting steps.

### Step 1 — Start the Controller (simple_controller.py)

```bash
# Terminal 1
source .venv/bin/activate
ryu-manager controller/simple_controller.py \
    --observe-links \
    --ofp-tcp-listen-port 6633 \
    --verbose
```

Expected startup output:
```
loading app controller/simple_controller.py
loading app ryu.controller.ofp_handler
...
[RYU] SimpleController initialised. Waiting for switches.
```

### Step 2 — Start Simple Topology

```bash
# Terminal 2
source .venv/bin/activate
sudo python topology/simple_topology.py
```

Expected controller output after switch connects:
```
[RYU] Switch connected: dpid=0000000000000001  OF version=4
[OPENFLOW] Table-miss flow installed on dpid=0000000000000001
[TOPOLOGY] Switch s1 (dpid=...) configured for OpenFlow 1.3
[TOPOLOGY] Simple topology ready.
```

### Step 3 — Test Connectivity

In the Mininet CLI (Terminal 2):
```
mininet> pingall
```

Expected output:
```
*** Ping: testing ping reachability
h1 -> h2
h2 -> h1
*** Results: 0% dropped (2/2 received)
```

Expected controller output after pingall:
```
[RYU] Learned: dpid=0000000000000001  mac=00:00:00:00:00:01 → port=1
[RYU] Learned: dpid=0000000000000001  mac=00:00:00:00:00:02 → port=2
[OPENFLOW] Flow installed: dpid=0000000000000001  00:00:00:00:00:02 → port=2
[OPENFLOW] Flow installed: dpid=0000000000000001  00:00:00:00:00:01 → port=1
```

### Step 4 — Verify Flow Rules

```bash
# From Mininet CLI or a separate terminal
mininet> sh ovs-ofctl -O OpenFlow13 dump-flows s1
```

Expected output (two learned flows + table-miss):
```
 cookie=0x0, duration=..., table=0, n_packets=..., priority=1,in_port=1,dl_src=00:00:00:00:00:01,dl_dst=00:00:00:00:00:02 actions=output:2
 cookie=0x0, duration=..., table=0, n_packets=..., priority=1,in_port=2,dl_src=00:00:00:00:00:02,dl_dst=00:00:00:00:00:01 actions=output:1
 cookie=0x0, duration=..., table=0, n_packets=..., priority=0 actions=CONTROLLER:65535
```

### Step 5 — Test Baseline Controller (learning_switch.py)

```bash
# Stop simple_controller.py (Ctrl+C in Terminal 1), then:
ryu-manager controller/learning_switch.py \
    --ofp-tcp-listen-port 6633

# Restart topology and retest
sudo mn --clean
sudo python topology/simple_topology.py
# In Mininet CLI:
mininet> pingall
```

Expected: same 0% drop result as with simple_controller.py.

### Step 6 — Cleanup

```bash
mininet> exit
bash scripts/cleanup.sh
```

---

## Phase 2 — Simple Topology Verification

> **LINUX-SIMULATION-REQUIRED**
> Status: Code complete (WINDOWS-DEV-TESTED). Linux execution pending.

### Step 0 — Prepare Ubuntu Machine

```bash
git pull origin main
source .venv/bin/activate
bash scripts/verify_linux_environment.sh
sudo service openvswitch-switch start
```

### Step 1 — Start Ryu Controller

```bash
# Terminal 1
ryu-manager controller/simple_controller.py \
  --observe-links \
  --ofp-tcp-listen-port 6633
```

### Step 2 — Start Simple Topology

```bash
# Terminal 2
sudo python topology/simple_topology.py
```

### Step 3 — Test Connectivity

In the Mininet CLI:
```
mininet> pingall
```
Expected: `0% dropped (2/2 received)`

### Step 4 — Automated Verification (no CLI)

```bash
sudo python topology/simple_topology.py --pingall --no-cli
echo "Exit code: $?"
```
Expected: exit code `0`

### Step 5 — Cleanup

```bash
bash scripts/cleanup.sh
```

---

## Demo Sequence

### Step 1 — Start the Controller

Open Terminal 1:

```bash
cd ai-predictive-self-healing-sdn
source .venv/bin/activate
ryu-manager controller/monitoring_controller.py \
  --observe-links \
  --ofp-tcp-listen-port 6633
```

Expected output:
```
loading app controller/monitoring_controller.py
loading app ryu.controller.ofp_handler
instantiating app controller/monitoring_controller.py
[RYU] Controller started. Listening on port 6633
```

### Step 2 — Start the Topology

Open Terminal 2:

```bash
cd ai-predictive-self-healing-sdn
source .venv/bin/activate
sudo python topology/campus_topology.py
```

Expected output:
```
[TOPOLOGY] Creating campus topology...
[TOPOLOGY] Switches: C1, D1, D2, A1, A2, A3, A4
[TOPOLOGY] Hosts: H1, H2, H3, H4
[TOPOLOGY] Starting network...
mininet>
```

### Step 3 — Verify Connectivity

In the Mininet CLI (Terminal 2):

```
mininet> pingall
```

Expected output:
```
*** Ping: testing ping reachability
H1 -> H2 H3 H4
H2 -> H1 H3 H4
H3 -> H1 H2 H4
H4 -> H1 H2 H3
*** Results: 0% dropped (12/12 received)
```

If pingall fails: see [docs/troubleshooting.md](troubleshooting.md).

### Step 4 — Show Normal Traffic and Monitoring

In Terminal 2 (Mininet CLI):

```
mininet> iperf H1 H4
```

In Terminal 1 (Ryu logs), observe monitoring output:
```
[MONITOR] Switch C1 Port 1: tx=12.4 Mbps util=6.2% loss=0.0% delay=1.2ms
[PREDICTION] Features: util=6.2, delay=1.2, loss=0.0 → NORMAL (conf=0.94)
```

### Step 5 — Demonstrate Congestion Detection

Open Terminal 3:

```bash
# Generate high-bandwidth traffic to saturate primary path
sudo mn --run "H1 iperf3 -c H4 -b 95M -t 120 &"
```

Or from Mininet CLI:
```
mininet> H1 iperf3 -c 10.0.0.4 -b 95M -t 120 &
```

Observe in Terminal 1:
```
[MONITOR] Switch D1 Port 2: tx=94.8 Mbps util=94.8% loss=2.1% delay=45ms
[PREDICTION] Features: util=94.8, delay=45.0, loss=2.1 → CONGESTION (conf=0.89)
[OPTIMIZER] Primary path H1→D1→C1→D2→H4: health_cost=0.87
[OPTIMIZER] Alternate path H1→D1→D2→H4: health_cost=0.31
[OPTIMIZER] Selected: H1→A1→D1→D2→A4→H4
[RYU] Installing flow rules for alternate path...
[OPENFLOW] FLOW_MOD sent to switches: D1, D2
[SELF-HEALING] Traffic rerouted. Recovery time: measured in ms
```

### Step 6 — Demonstrate Link Failure

From Mininet CLI:

```
mininet> link D1 C1 down
```

Observe in Terminal 1:
```
[MONITOR] OFPPortStatus: Switch D1 Port 3 → DOWN
[OPTIMIZER] Link D1-C1 failed. Evaluating alternate paths...
[OPTIMIZER] Alternate path available: H1→A1→D1→D2→A4→H4
[RYU] Installing failover flow rules...
[OPENFLOW] FLOW_MOD sent.
[SELF-HEALING] Failover complete. Recovery time: measured in ms
```

Verify connectivity maintained:
```
mininet> H1 ping -c 5 H4
```

### Step 7 — Restore Link

```
mininet> link D1 C1 up
```

### Step 8 — Show Results

```bash
# View monitoring CSV
cat experiments/results/latest_raw.csv | head -20

# View summary
cat experiments/results/latest_summary.json
```

### Step 9 — Show ML Prediction Standalone

```bash
# Run prediction on a sample feature vector
python ml/predict.py \
  --utilization 91 \
  --delay 48 \
  --packet_loss 3.2 \
  --traffic_rate 85 \
  --queue_length 18
```

Expected output:
```
[PREDICTION] Input: util=91, delay=48ms, loss=3.2%, rate=85Mbps
[PREDICTION] Label: CONGESTION
[PREDICTION] Confidence: 0.87
[PREDICTION] Probabilities: NORMAL=0.08, CONGESTION=0.87, FAILURE=0.05
```

### Step 10 — Show Path Optimizer Standalone

```bash
python routing/path_optimizer.py --demo
```

Expected output:
```
[OPTIMIZER] Topology: C1, D1, D2, A1, A2, A3, A4
[OPTIMIZER] Current path: H1→A1→D1→C1→D2→A4→H4  health_cost=0.85
[OPTIMIZER] Alternate:    H1→A1→D1→D2→A4→H4      health_cost=0.32
[OPTIMIZER] Selected:     H1→A1→D1→D2→A4→H4
```

### Step 11 — Cleanup

```bash
# In Mininet CLI
mininet> exit

# Cleanup
bash scripts/cleanup.sh
```

---

## Fallback Demo (if full integration not stable)

If the complete predictive pipeline is not stable at review time, demonstrate
the following components independently:

| Component | Command | Status |
|-----------|---------|--------|
| SDN topology | `sudo python topology/campus_topology.py` | LINUX-SIMULATION-REQUIRED |
| Connectivity | `pingall` in Mininet | LINUX-SIMULATION-REQUIRED |
| Monitoring output | Ryu logs | LINUX-SIMULATION-REQUIRED |
| ML prediction (standalone) | `python ml/predict.py --demo` | WINDOWS-COMPATIBLE |
| Path optimizer (standalone) | `python routing/path_optimizer.py --demo` | WINDOWS-COMPATIBLE |
| Health scorer (standalone) | `python routing/health_score.py --demo` | WINDOWS-COMPATIBLE |

Label any component not yet integrated as: "next integration phase".

---

## Timing (Estimated)

| Step | Duration |
|------|---------|
| Environment check | 2 min |
| Controller + topology start | 3 min |
| Normal traffic demo | 3 min |
| Congestion demo | 5 min |
| Failure + recovery demo | 5 min |
| Results and plots | 3 min |
| Q&A buffer | 5 min |
| **Total** | **~26 min** |
