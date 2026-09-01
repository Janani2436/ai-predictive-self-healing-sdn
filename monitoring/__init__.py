"""
monitoring package
LINUX-SIMULATION-REQUIRED (live data collection)
WINDOWS-COMPATIBLE (feature_extractor, unit tests with mock data)

Collects and processes network statistics from the Ryu SDN controller.

Modules:
    collector          — orchestrates all monitoring sources and polling loop
    port_stats         — parses OFPPortStatsReply (bytes, packets, errors)
    link_stats         — derives utilization (%) and traffic rate (Mbps)
    latency            — ICMP-based round-trip delay measurement
    packet_loss        — packet loss % from port error/drop counters
    feature_extractor  — assembles ML feature vector from raw stats
"""
