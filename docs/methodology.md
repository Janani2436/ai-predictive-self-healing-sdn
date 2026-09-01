# Methodology

## Research Approach

This project follows an emulation-based experimental methodology. A realistic
smart campus network is emulated using Mininet and Open vSwitch. Controlled
experiments are run to generate real network measurements, which feed an ML
pipeline and SDN control loop.

---

## Data Generation

### Source
All final training and evaluation data comes from Mininet experiments on the
personal Ubuntu/WSL2 simulation machine.

**Status: LINUX-SIMULATION-REQUIRED — not yet executed**

### Process
1. Start campus topology in Mininet
2. Start Ryu monitoring controller
3. Run traffic scenario (normal / congestion / failure)
4. Ryu polls OpenFlow port statistics every 5 seconds (configurable)
5. Measurements written to `dataset/raw/experiment_<id>_<scenario>.csv`
6. Each row is labelled with the traffic scenario class

### Dataset Schema

```
timestamp,source,destination,switch,port,throughput_mbps,delay_ms,
packet_loss_pct,utilization_pct,traffic_rate_mbps,queue_length,link_status,label
```

| Field | Type | Description |
|-------|------|-------------|
| timestamp | ISO 8601 | Measurement time |
| source | string | Source host (e.g., h1) |
| destination | string | Destination host (e.g., h4) |
| switch | string | Switch DPID or name |
| port | int | Switch port number |
| throughput_mbps | float | Measured throughput |
| delay_ms | float | ICMP round-trip delay / 2 |
| packet_loss_pct | float | Loss from port error counters |
| utilization_pct | float | tx_bytes delta / link capacity |
| traffic_rate_mbps | float | tx_bytes delta / interval |
| queue_length | int | OVS queue depth (if available) |
| link_status | int | 1 = up, 0 = down |
| label | string | NORMAL / CONGESTION / FAILURE |

### Class Labels

| Label | Trigger condition |
|-------|------------------|
| NORMAL | Baseline traffic, no injected faults |
| CONGESTION | High-bandwidth iperf3 flows saturating a link |
| FAILURE | Mininet link set to down |

### Labelling Strategy
Labels are applied programmatically based on the experiment script that
generated the data. Each scenario script sets the label column accordingly.
There is no post-hoc manual labelling.

---

## Feature Engineering

Initial feature set uses direct measurements from OpenFlow and ICMP.

If a feature cannot be reliably measured (e.g., queue_length on some OVS
configurations), it is omitted and documented as a limitation.

No feature fabrication. If a sensor is unavailable, the column is excluded
from that dataset version.

---

## Machine Learning

### Model Selection
Random Forest Classifier was selected because:
- Handles mixed feature types without extensive preprocessing
- Robust to small-to-medium datasets
- Provides feature importance ranking
- Interpretable for academic reporting
- No GPU or deep learning infrastructure required

### Training Procedure
1. Load and validate dataset (schema, ranges, missing values)
2. Report class distribution
3. If imbalanced: report and apply stratified split
4. Scale features (StandardScaler)
5. Stratified 80/20 train/test split
6. Train Random Forest with configurable hyperparameters
7. Evaluate on held-out test set
8. Save model with joblib, record metadata

### Hyperparameters (defaults)
```python
n_estimators = 100
max_depth = None  # grow until pure leaves
min_samples_split = 2
random_state = 42  # fixed for reproducibility
```

Hyperparameters may be tuned via cross-validation after baseline evaluation.
No tuning for artificial accuracy inflation.

### Evaluation Metrics
- Overall accuracy
- Per-class precision, recall, F1-score
- Confusion matrix (absolute counts and normalised)
- Feature importance ranking

All metrics reported only from models trained and evaluated on real experimental
data. Synthetic-data metrics are labelled SYNTHETIC-DATA / PRELIMINARY.

---

## Network Health Scoring

### Formula

```
health_cost = w_delay * norm(delay_ms)
            + w_loss  * norm(packet_loss_pct)
            + w_util  * norm(utilization_pct)
```

Where `norm()` normalises each metric to [0, 1] relative to defined maximum
values (configurable).

Default weights:
- w_delay = 0.40
- w_loss  = 0.35
- w_util  = 0.25

Higher cost = worse health = less preferred path.

Weights are configurable in `config.yaml`. They are engineering choices, not
scientifically optimal values. The rationale (delay and loss most impactful
for user experience) is documented but not claimed as validated.

### Failed Links
A link that is down (link_status = 0) receives health_cost = infinity and
is excluded from path selection.

---

## Path Optimization

The network topology is modelled as a directed graph using NetworkX.
Each edge has a dynamic weight equal to the current health cost of that link.

Algorithm: Dijkstra's shortest path (via networkx.shortest_path with weight
parameter).

At each decision cycle:
1. Update edge weights from current measurements
2. Remove failed links (weight = infinity or remove edge)
3. Find all simple paths between source and destination
4. Select path with minimum total weight
5. Log candidate paths and scores

---

## Routing Decision Cycle

```
Every monitoring interval:
    1. Collect port stats
    2. Extract features
    3. Predict condition (ML)
    4. If NORMAL: continue monitoring
    5. If CONGESTION or FAILURE:
        a. Score all candidate paths
        b. Find best alternative
        c. If better path exists: install new flow rules
        d. Log rerouting event and timestamp
        e. Begin measuring recovery
    6. After rerouting: confirm traffic on new path
    7. Record recovery time
```

---

## Baseline Comparison

### Baseline (Reactive)
- Standard reactive SDN: detect failure/congestion via polling
- Recalculate route only after problem is detected
- No ML prediction; responds to current state only

### Proposed (Predictive)
- ML predicts degradation before full failure
- Routes preemptively to healthier path
- Potentially lower recovery time and packet loss

### Comparison Methodology
- Same topology, same traffic scenarios
- Same monitoring interval
- Measure: recovery time, packet loss during event, throughput drop
- Report difference only from real executed experiments
- Do not claim superiority without experimental evidence

---

## Experiment Reproducibility

Each experiment script:
- Uses a fixed random seed where applicable
- Records experiment metadata (start time, topology, scenario, config snapshot)
- Saves raw CSV with timestamp-based filename
- Can be re-run independently

Results are stored in `experiments/results/` with experiment ID prefixes.
