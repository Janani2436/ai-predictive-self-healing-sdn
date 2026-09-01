---
inclusion: always
---

# Architecture

## System Overview

The system is a layered SDN simulation. Physical emulation runs entirely inside
Mininet on the personal Linux simulation machine. The Windows development machine
handles all logic that does not require live network interfaces.

## Layer Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      SMART CAMPUS NETWORK                    │
│                    (Mininet emulation)                        │
│                                                               │
│   H1   H2        H3   H4                                     │
│    │    │          │    │                                     │
│   A1   A2        A3   A4   (Access switches)                 │
│     \   \        /   /                                        │
│      D1 ─────────── D2    (Distribution switches)            │
│        \           /                                          │
│         ── CORE ──        (Core switch)                      │
└─────────────────────────────────────────────────────────────┘
                │  OpenFlow 1.3
┌───────────────▼─────────────────────────────────────────────┐
│                     RYU SDN CONTROLLER                        │
│                                                               │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────┐  │
│  │  Monitoring  │  │  Prediction  │  │ Path Optimization  │  │
│  │  Controller  │  │  Engine      │  │ (NetworkX)         │  │
│  └──────┬──────┘  └──────┬───────┘  └─────────┬──────────┘  │
│         │                │                      │             │
│         └────────────────▼──────────────────────┘            │
│                          │                                    │
│                   Health / Risk Score                         │
│                          │                                    │
│                   Best Path Selection                         │
│                          │                                    │
│                   Flow Rule Installation                      │
└──────────────────────────┬──────────────────────────────────┘
                           │  OpenFlow 1.3
                    OVS Switches
                           │
                    Traffic Rerouting
                           │
                    Self-Healing
                           │
                    Performance Data
```

## Module Responsibilities

### topology/
- Define Mininet network topologies in Python
- simple_topology.py: h1-s1-h2 (minimal verification topology)
- campus_topology.py: full smart-campus with redundant paths
- topology_utils.py: shared helpers (link creation, host config)
- LINUX-SIMULATION-REQUIRED: cannot be executed on Windows

### controller/
- Ryu SDN controller components (modular, one concern per file)
- simple_controller.py: OpenFlow 1.3 handshake, basic L2 forwarding
- learning_switch.py: MAC learning forwarding
- monitoring_controller.py: port/flow statistics collection
- predictive_controller.py: integrates ML prediction with flow management
- LINUX-SIMULATION-REQUIRED: Ryu requires Linux OpenFlow sockets

### monitoring/
- collector.py: orchestrates all monitoring sources
- port_stats.py: OpenFlow port statistics (tx/rx bytes, packets, errors)
- link_stats.py: derived link utilization and traffic rate
- latency.py: ICMP-based delay measurement
- packet_loss.py: loss calculation from port counters
- feature_extractor.py: transforms raw stats into ML feature vectors
- LINUX-SIMULATION-REQUIRED for live data; unit-testable on Windows with mock data

### traffic/
- traffic_generator.py: base class and orchestration
- normal_traffic.py: steady-state ping/iperf3 flows
- congestion_scenario.py: high-bandwidth flows to saturate links
- failure_scenario.py: programmatic link failure (Mininet link down)
- LINUX-SIMULATION-REQUIRED

### dataset/
- raw/: CSV files from individual experiments (git-ignored if large)
- processed/: cleaned, labelled, merged dataset for ML training
- README.md: dataset provenance, schema, labelling rules

### ml/
- preprocess.py: validation, cleaning, scaling, train/test split
- train.py: Random Forest training with configurable hyperparameters
- evaluate.py: accuracy, precision, recall, F1, confusion matrix
- predict.py: prediction API accepting feature dictionaries
- models/: persisted model files (.joblib) — git-ignored
- Fully executable on Windows (no Linux dependency)

### routing/
- health_score.py: weighted cost formula per link/path
- path_optimizer.py: NetworkX graph with dynamic edge weights
- route_manager.py: interface between optimizer and Ryu flow installation
- Fully executable on Windows for unit tests

### experiments/
- One script per experiment scenario
- Each saves raw CSV, processed CSV, event log, and summary JSON
- results/: experiment output (git-ignored if large)

### visualization/
- Matplotlib-based plots for reports and demo
- plots/: generated PNG files (git-ignored)

### scripts/
- verify_windows_environment.py: Windows-side dependency check
- verify_linux_environment.sh: Ubuntu-side full stack check
- setup_linux.sh: Ubuntu installation guide / automation
- run_demo.sh: end-to-end demo sequence
- cleanup.sh: safe process and state cleanup

### tests/
- Windows-executable unit tests only
- Use controlled synthetic data — never claim as real network results

### docs/
- Human-readable documentation for setup, architecture, methodology,
  experiments, demo commands, and troubleshooting

## Data Flow (Runtime)

```
Mininet hosts generate traffic
        │
OVS switches forward packets
        │
Ryu monitoring_controller polls port stats (every N seconds)
        │
feature_extractor builds feature vector
        │
predict.py → Random Forest → label (NORMAL / CONGESTION / FAILURE)
        │
health_score.py scores all candidate paths
        │
path_optimizer.py selects lowest-cost viable path
        │
route_manager.py instructs Ryu to install new flow rules
        │
Ryu sends OpenFlow FLOW_MOD to OVS switches
        │
Traffic rerouted → self-healing complete
        │
Performance metrics recorded
```

## Configuration
All tunable parameters live in a central config file (config.yaml or .env).
No hard-coded IPs, ports, weights, thresholds, or paths anywhere in source code.
