"""
routing package
WINDOWS-COMPATIBLE (health_score, path_optimizer)
LINUX-SIMULATION-REQUIRED (route_manager — requires Ryu)

Network health scoring and path optimization.

Modules:
    health_score    — weighted cost formula: f(delay, packet_loss, utilization)
    path_optimizer  — NetworkX graph with dynamic edge weights; finds optimal path
    route_manager   — translates optimal path to Ryu flow rule instructions
"""
