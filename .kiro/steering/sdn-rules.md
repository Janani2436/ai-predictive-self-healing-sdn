---
inclusion: always
---

# SDN Rules

## Controller: Ryu
- Use Ryu as the SDN controller. Do not replace it without explicit justification.
- Use OpenFlow 1.3 exclusively.
- If a genuine Ryu compatibility problem is found: identify the exact issue,
  explain it, propose the smallest viable fix, and confirm before proceeding.

## Controller Structure
- Do NOT put all logic in one Ryu application file.
- Separate concerns across files:
  - simple_controller.py: OF handshake, table-miss, basic forwarding
  - learning_switch.py: MAC-learning L2 forwarding
  - monitoring_controller.py: port/flow stats polling, CSV output
  - predictive_controller.py: ML integration, health scoring, rerouting
- Each file should be independently runnable as a Ryu app where practical.

## OpenFlow Rules
- Always set OpenFlow version explicitly to OFP_VERSION = [ofproto_v1_3.OFP_VERSION]
- Use table-miss flow entries with priority 0
- Install proactive flow rules for known paths; fall back to reactive only
  when topology is not yet fully learned
- Always match on in_port + eth_dst at minimum for unicast forwarding
- Use idle_timeout and hard_timeout appropriately — document the chosen values
- Never install permanent wildcard rules that could cause forwarding loops

## Topology
- The topology is EMULATED — no physical hardware
- All switches are Open vSwitch (OVS) instances inside Mininet
- The campus topology must have at least two distinct logical paths between
  at least one source-destination host pair
- Topology optimization = selecting a better logical path through the EXISTING
  topology — never physically rewiring

## Monitoring
- Poll port statistics via OpenFlow OFPPortStatsRequest every N seconds (configurable)
- Derive utilization from tx_bytes delta over the polling interval
- Do not fabricate statistics
- If a statistic cannot be reliably obtained, document why and omit it

## Flow Management
- Flow modifications must go through route_manager.py
- route_manager.py is the single point of contact between the optimizer and Ryu
- Log every flow installation and modification with [RYU] and [OPENFLOW] prefixes
- After a flow modification, verify forwarding by monitoring subsequent traffic

## Link Failure
- Simulate link failure using Mininet's link.intf1.setLink(up=False) or equivalent
- Detect failure via port status messages (OFPPortStatus) or polling
- On failure detection: immediately evaluate alternate paths
- If no alternate path exists: log "NO ALTERNATE PATH AVAILABLE" and do not fake recovery
- Recovery time = time from failure detection to restored end-to-end connectivity

## LINUX-SIMULATION-REQUIRED Boundary
All of the following CANNOT run on the Windows development machine:
- Mininet topology scripts
- Open vSwitch commands
- Ryu controller (requires Linux OpenFlow socket)
- iperf3 traffic generation
- ICMP-based latency measurement via Mininet hosts
- Any code that imports or calls Mininet APIs

Code that crosses this boundary must be clearly marked.
On Windows, these modules may be imported for static analysis but must not
be executed.

## Verification Status Labels
Apply these labels in code comments and documentation:

- WINDOWS-DEV-TESTED: logic verified by unit test on Windows machine
- LINUX-SIMULATION-REQUIRED: requires Mininet/OVS/Ubuntu to execute
- LINUX-TESTED: confirmed working on the personal Ubuntu simulation machine
- PLANNED: not yet implemented
