# Phase 4 — Linux Validation

## Environment

- Ubuntu 22.04 (WSL2)
- Mininet
- Open vSwitch
- Ryu Controller
- OpenFlow 1.3

## Campus Topology

- 7 OpenFlow switches
- 4 hosts
- Core/Distribution/Access hierarchy
- Redundant D1–D2 link
- Unique DPIDs assigned

## Baseline Connectivity

| Test | Result |
|------|--------|
| Controller connection | PASS |
| OpenFlow 1.3 | PASS |
| RSTP convergence | PASS |
| pingall | 0% packet loss |

## Failure Injection

Link disabled:

D1 ↔ D2

RSTP reconverged successfully.

| Observation | Result |
|------------|--------|
| Alternate path activated | YES |
| H1 ↔ H2 communication | PASS |
| Initial pingall | 16% loss |

## Link Restoration

After restoring D1–D2:

- RSTP restored loop-free topology.
- Reactive controller required relearning.
- Temporary packet loss observed during restoration.

## Conclusion

The Linux simulation successfully validated:

- redundant topology
- OpenFlow controller connectivity
- RSTP failover
- alternate path communication

This forms the baseline before AI-based predictive self-healing.
