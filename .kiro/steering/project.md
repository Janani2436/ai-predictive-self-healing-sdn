---
inclusion: always
---

# Project: AI-Driven Predictive Self-Healing SDN

## Title
AI-Driven Predictive Self-Healing Software-Defined Networking with Intelligent Topology Optimization for Smart Campus Networks

## Short Name
AI-Driven Predictive Self-Healing SDN

## Objective
Build a working simulation/emulation prototype of an AI-driven predictive self-healing SDN system for a smart campus network. The system demonstrates the full pipeline from network traffic through ML-based prediction to dynamic rerouting and self-healing.

## Pipeline
```
Network Traffic → Network Monitoring → Feature Extraction → ML Prediction
→ Network Health / Risk Assessment → Path Optimization → Ryu Controller
→ OpenFlow → Switch Flow Update → Traffic Rerouting → Self-Healing
→ Performance Measurement
```

## Two-Machine Development Model

### Machine 1 — Windows Work Laptop (DEVELOPMENT)
- Kiro is installed here
- Used for: coding, architecture, ML development, graph/path algorithms, unit testing, configuration, documentation, Git/GitHub
- MUST NOT: install WSL2, Ubuntu, Mininet, Open vSwitch, or Linux kernel networking
- DO NOT bypass corporate restrictions

### Machine 2 — Personal Windows Laptop (SIMULATION)
- Contains: WSL2 → Ubuntu → Python → Mininet → Open vSwitch → Ryu → OpenFlow 1.3 → iperf3
- Used for: actual Mininet/OVS/Ryu execution, traffic generation, monitoring, experiments, real data generation

## GitHub as Shared Source of Truth
- Never use machine-specific absolute paths
- Use relative paths everywhere
- Use configuration files / environment variables for machine-specific values

## Implementation Phases
1. Repository and environment documentation
2. Minimal Mininet topology (h1-s1-h2)
3. Ryu + OpenFlow integration
4. Redundant smart-campus topology
5. Traffic generation
6. Network monitoring
7. Dataset generation
8. Random Forest ML
9. Health scoring
10. Path optimization
11. Dynamic rerouting
12. Predictive self-healing integration
13. Experiments
14. Baseline comparison
15. Visualization
16. Final demonstration and documentation

## Current Status
Phase 1 — Repository structure and documentation. No Linux SDN components executed yet.
