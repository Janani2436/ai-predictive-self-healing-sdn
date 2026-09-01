# AI-Driven Predictive Self-Healing SDN

**AI-Driven Predictive Self-Healing Software-Defined Networking with Intelligent Topology Optimization for Smart Campus Networks**

Final-year engineering project.

---

## Status

| Component | Status |
|-----------|--------|
| Repository structure | ✅ Complete |
| Steering / configuration | ✅ Complete |
| Requirements files | ✅ Complete |
| Documentation skeleton | ✅ Complete |
| Mininet topology | 🔲 LINUX-SIMULATION-REQUIRED |
| Ryu controller | 🔲 LINUX-SIMULATION-REQUIRED |
| Traffic generation | 🔲 LINUX-SIMULATION-REQUIRED |
| Network monitoring | 🔲 LINUX-SIMULATION-REQUIRED |
| Dataset generation | 🔲 LINUX-SIMULATION-REQUIRED |
| ML pipeline (Random Forest) | 🔲 PLANNED |
| Health scoring | 🔲 PLANNED |
| Path optimization | 🔲 PLANNED |
| Dynamic rerouting | 🔲 PLANNED |
| Predictive self-healing | 🔲 PLANNED |
| Experiments | 🔲 PLANNED |
| Visualization | 🔲 PLANNED |

---

## Problem

Campus networks face unpredictable congestion, link failures, and traffic bursts
that traditional reactive networks handle poorly — detecting problems only after
they have already degraded user experience. By the time a fault is detected and
traffic rerouted manually or by a slow control plane, significant packet loss and
latency have already occurred.

---

## Proposed Solution

An AI-driven SDN system that:

1. Continuously monitors network statistics via OpenFlow
2. Extracts features from live traffic measurements
3. Uses a Random Forest classifier to predict network conditions
   (NORMAL / CONGESTION / FAILURE) before they fully manifest
4. Calculates a health/cost score for all candidate paths
5. Instructs the Ryu SDN controller to proactively reroute traffic
   to the healthiest available path
6. Measures and logs recovery time and performance improvement

---

## Architecture

```
                    SMART CAMPUS NETWORK (Mininet)
                             │
                    Open vSwitch (OVS)
                             │  OpenFlow 1.3
                      Ryu SDN Controller
                      ┌──────┼──────┐
                  Monitor  Predict  Optimize
                      └──────┼──────┘
                       Health Score
                             │
                       Best Path
                             │
                       Flow Update → OVS → Rerouting → Self-Healing
```

Full architecture diagram: [docs/architecture.md](docs/architecture.md)

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Network emulation | Mininet |
| Virtual switches | Open vSwitch (OVS) |
| SDN protocol | OpenFlow 1.3 |
| SDN controller | Ryu |
| Traffic generation | ping, iperf3 |
| ML model | Random Forest (scikit-learn) |
| Graph algorithms | NetworkX |
| Data processing | NumPy, Pandas |
| Visualisation | Matplotlib |
| Model persistence | joblib |
| Configuration | PyYAML, python-dotenv |

---

## Two-Machine Development Model

### Machine 1 — Windows Work Laptop (Development)
Used for: coding, unit testing, ML development, graph algorithms, documentation, Git.

**Does NOT run:** Mininet, OVS, Ryu, or any Linux networking.

```
Windows Work Laptop
  └── Kiro IDE
  └── Python 3.14
  └── Git
  └── Unit tests (pytest)
  └── ML pipeline development
  └── Path optimizer development
```

### Machine 2 — Personal Laptop (Simulation)
Used for: actual SDN emulation, experiment execution, real data collection.

```
Personal Windows Laptop
  └── WSL2
      └── Ubuntu
          └── Python 3
          └── Mininet
          └── Open vSwitch
          └── Ryu
          └── OpenFlow 1.3
          └── iperf3
```

### Workflow

```
Windows (Kiro) → Code → Git push → GitHub → Git pull → Ubuntu (WSL2) → Execute
                                                              │
                                          Bug reports / data ← Git push
```

---

## Installation

### Windows Development Machine

```bash
# Clone repository
git clone <repo-url>
cd ai-predictive-self-healing-sdn

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install development dependencies
pip install -r requirements-dev.txt

# Verify environment
python scripts/verify_windows_environment.py
```

### Ubuntu Simulation Machine (WSL2)

```bash
# Clone repository
git clone <repo-url>
cd ai-predictive-self-healing-sdn

# Run setup script
bash scripts/setup_linux.sh

# Verify environment
bash scripts/verify_linux_environment.sh
```

Full setup instructions: [docs/setup.md](docs/setup.md)

---

## Usage

> **Note:** All SDN simulation commands require the personal Ubuntu/WSL2 machine.
> Windows development machine can only run unit tests and ML pipeline components.

### Run demo (Linux only)
```bash
bash scripts/run_demo.sh
```

### Run unit tests (Windows)
```bash
pytest tests/
```

### Train ML model (Windows — using synthetic data for development)
```bash
python ml/train.py --dataset dataset/raw/synthetic_sample.csv
```

### Run experiments (Linux only)
```bash
python experiments/normal_experiment.py
python experiments/congestion_experiment.py
python experiments/failure_experiment.py
```

---

## Experiments

| Experiment | Scenario | Status |
|-----------|---------|--------|
| 1 | Normal traffic baseline | PLANNED |
| 2 | Congestion | PLANNED |
| 3 | Link failure + recovery | PLANNED |
| 4 | Increasing traffic load | PLANNED |
| 5 | Predictive rerouting | PLANNED |

Details: [docs/experiments.md](docs/experiments.md)

---

## ML Pipeline

```
Real Mininet dataset (CSV)
        │
Validation & Preprocessing
        │
Random Forest Classifier
        │
Evaluation (accuracy / precision / recall / F1 / confusion matrix)
        │
Saved model (joblib)
        │
Prediction API → label + confidence
```

> All ML metrics will be reported only from models trained on real experimental data.
> Synthetic-data results are clearly labelled as preliminary.

---

## Routing & Self-Healing

1. Monitor link stats via OpenFlow port statistics
2. Extract feature vector from current measurements
3. Random Forest predicts: NORMAL / CONGESTION / FAILURE
4. Health score calculated for all candidate paths
5. Path optimizer (NetworkX) selects lowest-cost viable path
6. Ryu installs updated flow rules via OpenFlow FLOW_MOD
7. Traffic rerouted — self-healing complete
8. Recovery time measured and logged

---

## Results

> No experimental results yet. All results will be generated from actual
> Mininet experiments on the personal simulation machine.
>
> Label: **LINUX-SIMULATION-REQUIRED**

---

## Limitations (Current)

- No real network experiments executed yet (Linux simulation machine not yet configured)
- ML model not yet trained on real data
- Ryu/OpenFlow integration not yet verified
- All performance claims require Linux execution to validate

---

## Future Work

- XGBoost comparison model
- Multi-failure scenario handling
- RECOVERY class in ML model
- Real-time dashboard
- Extended campus topology

---

## Documentation

| Document | Description |
|---------|-------------|
| [docs/setup.md](docs/setup.md) | Installation guide (Windows + Ubuntu) |
| [docs/architecture.md](docs/architecture.md) | System architecture |
| [docs/methodology.md](docs/methodology.md) | Research methodology |
| [docs/experiments.md](docs/experiments.md) | Experiment descriptions |
| [docs/review_demo.md](docs/review_demo.md) | Step-by-step demo commands |
| [docs/troubleshooting.md](docs/troubleshooting.md) | Common issues and fixes |
