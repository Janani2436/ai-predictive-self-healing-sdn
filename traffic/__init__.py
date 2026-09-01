"""
traffic package
LINUX-SIMULATION-REQUIRED

Traffic generation scripts for experiment scenarios.
Uses ping and iperf3 via Mininet host commands.

Modules:
    traffic_generator    — base class; configurable source, dest, bandwidth, duration
    normal_traffic       — low-rate background traffic (ping + iperf3)
    congestion_scenario  — high-bandwidth flows to saturate links
    failure_scenario     — programmatic Mininet link failure/recovery
"""
