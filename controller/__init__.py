"""
controller package
LINUX-SIMULATION-REQUIRED

Modular Ryu SDN controller components.
Each module is a separate concern and independently runnable as a Ryu app.

Modules:
    simple_controller      — OpenFlow 1.3 handshake, table-miss, basic forwarding
    learning_switch        — reactive MAC-learning L2 forwarding (baseline)
    monitoring_controller  — periodic port/flow stats polling, CSV output
    predictive_controller  — ML prediction integration, health scoring, rerouting
"""
