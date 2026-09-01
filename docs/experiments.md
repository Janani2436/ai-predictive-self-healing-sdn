# Experiments

> **Status: LINUX-SIMULATION-REQUIRED**
> None of these experiments have been executed yet.
> All descriptions are planned methodology.
> Results will be added after execution on the personal Ubuntu/WSL2 machine.

---

## Common Setup (All Experiments)

Before any experiment:
1. Start Open vSwitch: `sudo service openvswitch-switch start`
2. Start Ryu controller: `ryu-manager controller/monitoring_controller.py`
3. Start Mininet topology: `sudo python topology/campus_topology.py`
4. Verify connectivity: `pingall` in Mininet CLI
5. Confirm OpenFlow connection in Ryu logs

After any experiment:
1. Save results from `experiments/results/`
2. Run `bash scripts/cleanup.sh`

---

## Experiment 1 — Normal Traffic Baseline

**Script:** `experiments/normal_experiment.py`

**Objective:** Establish baseline measurements under normal operating conditions.

**Procedure:**
1. Start campus topology
2. Generate background ping between all host pairs
3. Run low-rate iperf3 UDP flows (configurable bandwidth, default 10 Mbps)
4. Collect measurements for 5 minutes (configurable)
5. Save CSV with label = NORMAL

**Expected observations:**
- Low utilization (< 50%)
- Low delay (< 10 ms in emulation)
- Near-zero packet loss

**Output files:**
- `experiments/results/exp1_<timestamp>_raw.csv`
- `experiments/results/exp1_<timestamp>_summary.json`

**Status: PLANNED — LINUX-SIMULATION-REQUIRED**

---

## Experiment 2 — Congestion

**Script:** `experiments/congestion_experiment.py`

**Objective:** Generate and measure network congestion. Verify that the system
detects congestion and selects an alternate path.

**Procedure:**
1. Start campus topology
2. Begin normal background traffic
3. After 60 seconds: inject high-bandwidth iperf3 TCP flows on primary path
   (target: saturate the A1-D1 or D1-C1 link)
4. Continue for 3 minutes
5. Observe: ML prediction transitions to CONGESTION
6. Observe: path optimizer selects alternate path
7. Observe: Ryu installs new flow rules
8. Record recovery time (time from CONGESTION detection to rerouting complete)
9. Remove congestion source, observe return to NORMAL

**Measurements to record:**
- Throughput before / during / after congestion
- Delay before / during / after
- Packet loss during congestion
- Time from congestion onset to detection
- Time from detection to flow rule update
- Time from flow rule update to stable alternate path

**Output files:**
- `experiments/results/exp2_<timestamp>_raw.csv`
- `experiments/results/exp2_<timestamp>_events.log`
- `experiments/results/exp2_<timestamp>_summary.json`

**Status: PLANNED — LINUX-SIMULATION-REQUIRED**

---

## Experiment 3 — Link Failure and Recovery

**Script:** `experiments/failure_experiment.py`

**Objective:** Simulate a hard link failure and measure the system's recovery
capability.

**Procedure:**
1. Start campus topology with traffic flowing H1 → H4 via Path A
2. After 60 seconds: bring down D1-C1 link (Mininet link down)
3. Observe: Ryu receives OFPPortStatus DOWN notification (or detects via polling)
4. Observe: path optimizer identifies Path B as alternative
5. Observe: Ryu installs flow rules for Path B
6. Measure: time from link-down to traffic flowing on Path B (recovery time)
7. After 3 minutes: restore link (Mininet link up)
8. Observe: system may return to original path or remain on Path B

**Measurements to record:**
- Packet loss during failover window
- Recovery time (ms)
- Whether connectivity was maintained
- Path before and after failure

**If no alternate path exists:** System logs "NO ALTERNATE PATH AVAILABLE".
This is a valid experimental outcome, not a failure.

**Output files:**
- `experiments/results/exp3_<timestamp>_raw.csv`
- `experiments/results/exp3_<timestamp>_events.log`
- `experiments/results/exp3_<timestamp>_summary.json`

**Status: PLANNED — LINUX-SIMULATION-REQUIRED**

---

## Experiment 4 — Increasing Traffic Load

**Script:** `experiments/congestion_experiment.py` (with ramp configuration)

**Objective:** Observe system behaviour under gradually increasing load.
Validate that the ML model detects the NORMAL → CONGESTION transition.

**Procedure:**
1. Start campus topology
2. Begin at 10% link utilization
3. Increase iperf3 bandwidth every 60 seconds: 10% → 30% → 50% → 70% → 90%
4. Record measurements at each step
5. Observe ML prediction at each step
6. Note the utilization level at which CONGESTION is first predicted

**Output files:**
- `experiments/results/exp4_<timestamp>_raw.csv`
- `experiments/results/exp4_<timestamp>_summary.json`

**Status: PLANNED — LINUX-SIMULATION-REQUIRED**

---

## Experiment 5 — Predictive Rerouting

**Script:** `experiments/predictive_experiment.py`

**Objective:** Demonstrate proactive rerouting where the ML model predicts
congestion before the link is fully saturated, and the system reroutes
preemptively.

**Procedure:**
1. Train ML model on data from Experiments 1-4
2. Start campus topology
3. Begin gradual traffic increase toward a link
4. Monitor: at what utilization level does the model predict CONGESTION?
5. Observe: does the system reroute before the link reaches full saturation?
6. Compare recovery time and packet loss against Experiment 2 (reactive)

**Note:** If the ML model only predicts CONGESTION after the link is already
saturated, the system is classified as **REACTIVE SELF-HEALING**. If it
predicts and reroutes before saturation, it is classified as
**PREDICTIVE SELF-HEALING**.

Do not claim predictive behaviour without experimental evidence.

**Output files:**
- `experiments/results/exp5_<timestamp>_raw.csv`
- `experiments/results/exp5_<timestamp>_events.log`
- `experiments/results/exp5_<timestamp>_summary.json`

**Status: PLANNED — LINUX-SIMULATION-REQUIRED**

---

## Baseline Comparison Experiment

**Script:** `experiments/congestion_experiment.py` with `--mode baseline`

**Objective:** Run identical scenarios with a conventional reactive SDN
controller (no ML, no health scoring) to establish a comparison baseline.

**Baseline controller behaviour:**
- Polls link stats
- Detects congestion/failure when threshold exceeded
- Recalculates shortest path (hop count only)
- Installs new flows reactively

**Proposed system behaviour:**
- ML predicts condition
- Health-aware path selection
- Proactive or rapid reactive rerouting

**Comparison metrics:**
- Recovery time (seconds)
- Packet loss during event (%)
- Throughput drop (Mbps)
- Time to stable state

Do not report comparison results without completing both experiments.

**Status: PLANNED — LINUX-SIMULATION-REQUIRED**

---

## Result Storage Convention

All experiment outputs follow this naming convention:

```
experiments/results/
  exp<N>_<YYYYMMDD_HHMMSS>_raw.csv        — raw measurements
  exp<N>_<YYYYMMDD_HHMMSS>_events.log     — timestamped event log
  exp<N>_<YYYYMMDD_HHMMSS>_summary.json   — summary statistics
```

Summary JSON format:
```json
{
  "experiment_id": "exp3_20260101_120000",
  "scenario": "link_failure",
  "topology": "campus",
  "duration_seconds": 300,
  "recovery_time_ms": null,
  "status": "PLANNED",
  "notes": "Not yet executed"
}
```
