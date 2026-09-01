---
inclusion: always
---

# Research Integrity

## Core Principle
This is an academic final-year engineering project. Every numerical result
presented in reports, demos, or documentation must be traceable to an actual
executed experiment.

## What Must Never Be Fabricated
- Network throughput measurements
- End-to-end latency / delay values
- Packet loss percentages
- Link utilization percentages
- Traffic rates
- Queue lengths
- Recovery time measurements
- ML accuracy, precision, recall, F1-score values
- Confusion matrix entries
- Improvement percentages over baseline
- Any comparative claims ("X% better than baseline")

## Mandatory Labels
Every result, metric, or claim must carry one of these labels:

| Label | Meaning |
|-------|---------|
| WINDOWS-DEV-TESTED | Logic verified by unit test on Windows; no live network involved |
| SYNTHETIC-DATA | Generated programmatically for pipeline testing only |
| LINUX-SIMULATION-REQUIRED | Requires Mininet/OVS/Ubuntu; not yet executed |
| LINUX-TESTED | Confirmed by actual execution on the personal simulation machine |
| PRELIMINARY | Early result; methodology or data not yet finalised |
| PLANNED | Feature designed but not yet implemented |

## Synthetic Data Rules
Synthetic / mock data may be used on Windows for:
- Unit testing pipeline logic
- Verifying data schema handling
- Developing and debugging algorithms before real data exists

Synthetic data must:
- Be stored in dataset/raw/ with filenames prefixed synthetic_
- Contain a header comment or README note stating it is synthetic
- NEVER be used to report final experimental performance
- NEVER appear in academic reports as real experimental data

## Real Experimental Data
Real data is data collected from actual Mininet experiments running on
the personal Ubuntu/WSL2 simulation machine.

Real data must:
- Be stored in dataset/raw/ with filenames prefixed experiment_
- Include experiment metadata: date, topology, scenario, duration, seed
- Be reproducible (same scenario script should produce comparable results)

## Claims in Documentation
When writing docs, comments, or README sections:

Use:
  "Unit-tested on Windows with synthetic data."
  "Requires Linux execution — not yet verified."
  "Preliminary result from synthetic dataset."

Never use:
  "The system achieves 94% accuracy."  (unless from a real trained+evaluated model)
  "Recovery time is 2.3 seconds."      (unless measured in a real experiment)
  "30% improvement over baseline."     (unless from real comparative experiments)

## Code Comments
When a function returns a hardcoded or placeholder value pending real data:

```python
# TODO: Replace with value from real Mininet experiment
# SYNTHETIC placeholder — do not cite in reports
return 0.0
```

## Kiro Behaviour Rule
Kiro must not:
- Generate fake network statistics as if they were real measurements
- Claim that any Mininet/OVS/Ryu feature works unless it has been executed
  on the personal Linux simulation machine
- Present synthetic ML metrics as real model performance
- Write documentation stating performance claims without experimental evidence

When uncertain whether a result is real or synthetic, Kiro must label it
as SYNTHETIC or PRELIMINARY and explain what is needed to obtain real results.
