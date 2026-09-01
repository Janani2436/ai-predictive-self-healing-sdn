# System Architecture

## Overview

The system is a layered SDN emulation pipeline. Network emulation runs in
Mininet on the personal Ubuntu/WSL2 machine. All AI, ML, and routing logic
is developed on the Windows work laptop and executed in the Linux environment.

---

## Full Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     SMART CAMPUS NETWORK                         │
│                      (Mininet emulation)                         │
│                                                                   │
│   H1    H2              H3    H4                                 │
│    │     │               │     │                                 │
│  [A1]  [A2]           [A3]  [A4]    ← Access layer switches     │
│     \    \             /    /                                     │
│     [D1] ────────── [D2]           ← Distribution switches      │
│        \            /                                             │
│         ──── [C1] ────             ← Core switch                 │
│                                                                   │
│   Open vSwitch instances — all OpenFlow 1.3                      │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                    OpenFlow 1.3 (TCP port 6633)
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                      RYU SDN CONTROLLER                           │
│                                                                   │
│  ┌──────────────────┐  ┌─────────────────┐  ┌────────────────┐  │
│  │ monitoring_       │  │ predict.py      │  │ path_          │  │
│  │ controller.py     │  │ (Random Forest) │  │ optimizer.py   │  │
│  │                   │  │                 │  │ (NetworkX)     │  │
│  │ Port stats poll   │  │ Feature vector  │  │ Edge weights   │  │
│  │ Link utilization  │  │ → NORMAL /      │  │ from health    │  │
│  │ Packet loss       │  │   CONGESTION /  │  │ scores         │  │
│  │ Delay             │  │   FAILURE       │  │                │  │
│  └────────┬──────────┘  └──────┬──────────┘  └───────┬────────┘  │
│           │                    │                      │           │
│           └────────────────────▼──────────────────────┘           │
│                                │                                  │
│                        health_score.py                            │
│                    (weighted cost per path)                        │
│                                │                                  │
│                        route_manager.py                           │
│                    (best path → flow rules)                        │
│                                │                                  │
│                   OpenFlow FLOW_MOD messages                      │
└────────────────────────────────┬─────────────────────────────────┘
                                 │
                          OVS switches update
                                 │
                         Traffic rerouted
                                 │
                          Self-healing complete
                                 │
                         Performance metrics logged
```

---

## Component Descriptions

### topology/

Defines the Mininet network topology in Python.

- `simple_topology.py` — minimal h1-s1-h2 topology for initial verification
- `campus_topology.py` — full campus topology with redundant paths (C1, D1, D2, A1-A4, H1-H4)
- `topology_utils.py` — shared helpers for link creation, host IP assignment, OVS configuration

**Platform:** LINUX-SIMULATION-REQUIRED

### controller/

Modular Ryu SDN controller components. Each file is a separate concern.

- `simple_controller.py` — OpenFlow 1.3 handshake, table-miss entry, basic packet-in handler
- `learning_switch.py` — reactive MAC-learning L2 forwarding (baseline)
- `monitoring_controller.py` — periodic OFPPortStatsRequest, CSV output of measurements
- `predictive_controller.py` — integrates ML prediction, health scoring, proactive rerouting

**Platform:** LINUX-SIMULATION-REQUIRED (Ryu requires Linux OpenFlow socket)

### monitoring/

Collects and processes network statistics from the controller.

- `collector.py` — orchestrates all monitoring sources, drives polling loop
- `port_stats.py` — parses OFPPortStatsReply (tx/rx bytes, packets, errors, drops)
- `link_stats.py` — derives utilization (%) and traffic rate (Mbps) from byte deltas
- `latency.py` — ICMP-based round-trip delay via Mininet host.cmd('ping')
- `packet_loss.py` — loss percentage from port error/drop counters
- `feature_extractor.py` — assembles ML feature vector from raw stats

**Platform:** Live data requires LINUX-SIMULATION-REQUIRED; feature_extractor is WINDOWS-COMPATIBLE

### traffic/

Traffic generation for experiment scenarios.

- `traffic_generator.py` — base class; configurable source, destination, bandwidth, duration
- `normal_traffic.py` — low-rate ping + iperf3 background flows
- `congestion_scenario.py` — high-bandwidth iperf3 flows to saturate links
- `failure_scenario.py` — programmatic link down/up via Mininet API

**Platform:** LINUX-SIMULATION-REQUIRED

### dataset/

Stores raw and processed network measurement data.

- `raw/` — CSV files from individual Mininet experiments (prefixed `experiment_`)
- `processed/` — cleaned, labelled, merged dataset ready for ML training
- Synthetic test data prefixed `synthetic_` — for Windows-side pipeline testing only

### ml/

Machine learning pipeline — fully Windows-compatible.

- `preprocess.py` — schema validation, cleaning, feature scaling, stratified split
- `train.py` — Random Forest training with configurable hyperparameters
- `evaluate.py` — accuracy, precision, recall, F1, confusion matrix; saves plots
- `predict.py` — inference API: accepts feature dict, returns label + confidence
- `models/` — saved .joblib model files (git-ignored)

**Platform:** WINDOWS-COMPATIBLE

### routing/

Network health scoring and path optimization — fully Windows-compatible.

- `health_score.py` — weighted cost formula: f(delay, packet_loss, utilization)
- `path_optimizer.py` — NetworkX graph with dynamic edge weights; finds optimal path
- `route_manager.py` — translates optimal path into Ryu flow rule instructions

**Platform:** health_score.py and path_optimizer.py are WINDOWS-COMPATIBLE; route_manager.py requires Ryu (LINUX-SIMULATION-REQUIRED)

### experiments/

End-to-end experiment scripts, one per scenario.

Each script:
1. Starts topology
2. Starts controller
3. Generates traffic
4. Collects measurements
5. Saves results to `experiments/results/`

**Platform:** LINUX-SIMULATION-REQUIRED

### visualization/

Matplotlib plots for reports and demo.

- `plot_metrics.py` — time-series of throughput, delay, loss, utilization
- `plot_comparison.py` — baseline vs proposed system comparison
- `plot_recovery.py` — recovery time analysis
- All plots saved to `visualization/plots/`

**Platform:** WINDOWS-COMPATIBLE (uses saved CSV data)

---

## Data Flow Detail

### Monitoring Cycle (runs on Linux, every N seconds)

```
Ryu controller polls OFPPortStatsRequest
    → port_stats.py parses reply
    → link_stats.py calculates utilization and rate
    → packet_loss.py calculates loss from drop counters
    → latency.py measures delay via ping
    → feature_extractor.py assembles: {
          throughput_mbps, delay_ms, packet_loss_pct,
          utilization_pct, traffic_rate_mbps, queue_length, link_status
      }
    → written to CSV (dataset/raw/experiment_<id>.csv)
```

### Prediction and Rerouting Cycle

```
feature_extractor output
    → predict.py loads ml/models/current model
    → Random Forest inference → label + confidence
    → health_score.py scores all paths in graph
    → path_optimizer.py selects minimum-cost path
    → route_manager.py sends FLOW_MOD via Ryu
    → OVS switches update forwarding tables
    → traffic follows new path
    → recovery time measured
```

---

## Phase 2 Implementation Status

### topology/simple_topology.py — WINDOWS-DEV-TESTED (structure); LINUX-SIMULATION-REQUIRED (execution)

Implements the minimal `H1 --- S1 --- H2` topology.

Key design decisions:
- Mininet is imported **inside** `build()`, not at module level. This allows
  `simple_topology.py` to be imported on Windows for syntax/structure testing
  without immediately failing on a missing Mininet import.
- `build()` raises `ImportError` on Windows with a clear message pointing to
  the Ubuntu setup guide.
- `stop()` is always safe to call, even before `build()`.
- All parameters (controller IP/port, link bandwidth, delay) are configurable
  via CLI arguments or `config.yaml` — no hard-coded values.

### topology/topology_utils.py — WINDOWS-COMPATIBLE (pure functions); LINUX-SIMULATION-REQUIRED (OVS calls)

Contains:
- `load_config()` — reads `config.yaml`, falls back to safe defaults
- `get_controller_config()` — extracts controller host/port
- `format_host_ip()` — generates host IPs from subnet + number
- `make_link_params()` — builds Mininet TCLink parameter dicts
- `configure_ovs_openflow13()` — OVS configuration (Linux only)
- `verify_openflow_version()` — OpenFlow version check (Linux only)

---

## Phase 3 Implementation Status

### controller/simple_controller.py — WINDOWS-DEV-TESTED (structure); LINUX-SIMULATION-REQUIRED (execution)

Primary Ryu application for this project. Key design decisions:

- Ryu imports are at **module level** (not deferred). This is required because
  Ryu's `@set_ev_cls` decorator is evaluated at import time — deferring imports
  would break the event registration. On Windows, importing this file will fail
  with `ImportError: No module named 'ryu'`. This is expected and correct.
- `OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]` declared at class level.
  This is what tells Ryu to negotiate OpenFlow 1.3 with all connecting switches.
- Table-miss entry uses `priority=0`, `idle_timeout=0`, `hard_timeout=0`
  (permanent). It must never be removed while the controller is running.
- Learned flows use `idle_timeout=30`, `hard_timeout=120` to prevent stale
  entries from accumulating after MAC addresses move.
- `OFPCML_NO_BUFFER` on the table-miss action ensures the full packet is sent
  to the controller for learning, not just the header.
- `_fmt_dpid()` formats datapath IDs as 16-digit hex for readable log output.

### controller/learning_switch.py — WINDOWS-DEV-TESTED (structure); LINUX-SIMULATION-REQUIRED (execution)

Standalone baseline controller. Functionally equivalent to simple_controller.py
at Phase 3 level, but designed to remain a simple reactive-only controller
permanently — it will not gain monitoring or ML features in later phases.
Used as the conventional-SDN comparator in Phase 14 baseline experiments.

### Ryu Compatibility Fix

`requirements-linux.txt` had `eventlet==0.40.0` which breaks Ryu at startup.
Fixed to `eventlet==0.33.3`. See `docs/ryu_compatibility.md` for full analysis.

---

## OpenFlow Version

All controllers use **OpenFlow 1.3** exclusively.

```python
OFP_VERSION = [ofproto_v1_3.OFP_VERSION]
```

Controller listens on TCP port 6633 (configurable in config.yaml).

---

## Redundant Path Design

The campus topology guarantees at least two distinct logical paths between H1 and H4:

- Path A: H1 → A1 → D1 → C1 → D2 → A4 → H4
- Path B: H1 → A1 → D1 → D2 → A4 → H4  (via D1-D2 direct link)

If any single link on Path A fails, Path B remains available.
The path optimizer selects between these based on current health scores.
