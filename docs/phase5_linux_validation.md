# Phase 5 — Traffic Generation Linux Validation

## Status

**LINUX-TESTED**

Phase 5 traffic generation was implemented and executed in the Ubuntu 22.04 WSL2 simulation environment using Mininet, Open vSwitch, Ryu and iperf3.

## Environment

- Ubuntu 22.04.5 LTS
- Python 3.10.12
- Mininet 2.3.0
- Open vSwitch 2.17.12
- Ryu 4.34
- iperf3 3.9
- OpenFlow 1.3
- 7-switch redundant smart-campus topology
- 4 hosts

## Normal Traffic Validation

Two UDP flows were generated sequentially:

- H1 → H2 at 5 Mbps for 10 seconds
- H3 → H4 at 5 Mbps for 10 seconds

The recorded iperf3 results showed approximately 5 Mbps sender rate with 0% packet loss.

The measured jitter was approximately 0.060 ms for H1 → H2 and 0.086 ms for H3 → H4 in the recorded run.

## Controlled Congestion Validation

A deliberate contention scenario was implemented using two simultaneous UDP flows:

- H1 → H4 at 80 Mbps
- H2 → H4 at 80 Mbps

Both flows share the H4 access link, which is configured at 100 Mbps.

The combined offered load is therefore approximately 160 Mbps against the shared 100 Mbps link.

Actual iperf3 results recorded substantial packet loss during these runs. One recorded H1 → H4 run reported approximately 43.416% packet loss, demonstrating that the controlled traffic scenario can produce observable congestion-related packet loss.

The 80 Mbps values represent the configured/sender-reported offered traffic rate and are not interpreted as receiver throughput.

## Connectivity Validation

The Phase 5 runner also verified host connectivity before and after traffic generation.

The final connectivity check completed with:

- 0% packet loss
- 12/12 host-to-host connectivity checks successful

## Integrity Notes

All reported traffic values are taken from actual iperf3 output generated during Linux/WSL2 execution.

No synthetic throughput, latency or packet-loss values are used as experimental results.

Generated traffic JSONL files are retained locally as experimental evidence and are not treated as source-code files.

## Known Observation

The Mininet topology produced `sch_htb` quantum warnings while creating 100 Mbps traffic-controlled links. This is retained as an implementation observation and should be addressed before using the environment for detailed throughput benchmarking.

## Conclusion

Phase 5 traffic generation is implemented and Linux-tested. Normal traffic generation, simultaneous high-rate traffic and controlled congestion with measurable packet loss have been demonstrated in the real Mininet/OVS/Ryu environment.
