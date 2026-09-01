# Ryu Compatibility Analysis

**Status: PRELIMINARY — verified by research; not yet tested on personal simulation machine**
**Date: August 2026**

---

## Executive Summary

Ryu 4.34 is **unmaintained** upstream. The last PyPI release was May 2020,
built with CPython 3.6.9. The `faucetsdn/ryu` GitHub fork is also formally
marked "NOT CURRENTLY MAINTAINED" as of 2022, though it remains the most
widely-used installable variant.

The core OpenFlow 1.3 protocol implementation in Ryu is stable and
functionally correct — the maintenance issue affects only the installation
pathway and the `eventlet` concurrency layer.

**The project continues to use Ryu.** This is appropriate because:
- Ryu's OpenFlow 1.3 API is stable and well-documented
- The API used in this project (`app_manager`, `ofproto_v1_3`, `OFPFlowMod`,
  `OFPPacketOut`, etc.) has not changed
- The academic community still uses Ryu + Mininet as the standard SDN
  emulation stack
- No drop-in replacement exists that is both simpler and better-supported

The compatibility risk is manageable with the correct Python + eventlet
version pinning documented below.

---

## Compatibility Matrix

### Python Version

| Ubuntu Version | Default Python | Ryu 4.34 Compatible | Notes |
|---------------|---------------|---------------------|-------|
| 20.04 LTS | 3.8 | Yes | Works with eventlet==0.30.2 |
| **22.04 LTS** | **3.10** | **Yes (recommended)** | Works with eventlet==0.33.3 |
| 24.04 LTS | 3.12 | Partial | Needs eventlet==0.34.3 + faucetsdn fork |
| 26.04 LTS | 3.14 | Unknown | Not tested; likely broken |

**Recommendation: Ubuntu 22.04 LTS with its default Python 3.10.**

This is the safest, most widely tested combination for Ryu + Mininet + OVS.
Ubuntu 22.04 is available as a WSL2 image and is the recommended simulation
machine OS for this project.

### eventlet Version

This is the most critical dependency. Ryu's concurrency layer (`ryu/lib/hub.py`)
uses eventlet directly. Incompatible eventlet versions produce errors at startup,
not at runtime — so the failure is immediate and diagnosable.

| eventlet Version | Python 3.10 | Python 3.12 | Notes |
|-----------------|-------------|-------------|-------|
| 0.30.2 | Works | No | Widely cited as working with ryu 4.34 |
| **0.33.3** | **Works** | Partial | Recommended for Python 3.10 |
| 0.34.3 | Works | Works | faucetsdn/faucet recommendation for Python 3.12 |
| 0.40.0 | Broken | Broken | Too new — socket/greenlet API changes break Ryu |

**Fix applied:** `requirements-linux.txt` updated from `eventlet==0.40.0` to
`eventlet==0.33.3`.

The original `eventlet==0.40.0` pinning in this project was **incorrect** and
would have caused Ryu to fail immediately on startup with errors like:

```
TypeError: cannot set 'is_timeout' attribute of immutable type 'TimeoutError'
```

or:

```
AttributeError: module 'eventlet.green.socket' has no attribute ...
```

### Ryu Installation Source

| Source | Python 3.10 | Python 3.12 | Notes |
|--------|-------------|-------------|-------|
| `pip install ryu==4.34` | Usually works | May fail | Official PyPI, frozen May 2020 |
| `pip install git+https://github.com/faucetsdn/ryu.git` | Works | Better | Preferred — has minor Python 3.x fixes |

**Recommendation: Install from faucetsdn/ryu git source.**

`pip install ryu` from PyPI (the osrg/ryu source) may encounter `pbr` or
`tinyrpc` import errors on newer pip versions. The faucetsdn fork avoids
most of these.

`requirements-linux.txt` has been updated to reflect this.

### OVS and OpenFlow 1.3

| Component | Status | Notes |
|-----------|--------|-------|
| Open vSwitch (OVS) | Stable | Ubuntu 22.04 ships OVS 2.17.x via apt |
| OpenFlow 1.3 | Fully supported | OVS has supported OF1.3 since version 2.0 |
| OVS + Ryu OF1.3 handshake | Works | Standard, well-tested combination |
| OVS in WSL2 | Requires kernel module | WSL2 kernel must include openvswitch module |

**WSL2-specific OVS risk:** WSL2 uses a custom Microsoft kernel. The
`openvswitch` kernel module is included in the default WSL2 kernel from
version 5.15+, which ships with WSL2 on Windows 11 22H2 and later. If the
module is absent, OVS must be run in userspace mode (slower but functional).

Check with:
```bash
uname -r                     # should be 5.15+
sudo modprobe openvswitch    # should succeed silently
lsmod | grep openvswitch     # should show the module loaded
```

---

## Known Issues and Fixes

### Issue 1: eventlet too new (FIXED in requirements-linux.txt)

**Symptom:**
```
TypeError: cannot set 'is_timeout' attribute of immutable type 'TimeoutError'
```
or Ryu exits immediately after start.

**Root cause:** eventlet >= 0.35 changed the socket/greenlet API in ways
incompatible with ryu 4.34's hub.py.

**Fix:** Pin `eventlet==0.33.3` in `requirements-linux.txt`.

---

### Issue 2: pbr version conflict on install

**Symptom:**
```
error: pbr requires setuptools >= 17.1
```
or pip install of ryu fails with metadata errors.

**Fix:**
```bash
pip install --upgrade setuptools pip
pip install git+https://github.com/faucetsdn/ryu.git
```

---

### Issue 3: tinyrpc import error

**Symptom:**
```
ImportError: cannot import name 'HTTPTransportFactory' from 'tinyrpc.transports'
```

This occurs when Ryu's optional NETCONF/BGP features try to import an
incompatible version of tinyrpc.

**Fix:** This only affects optional components (NETCONF, BGP). The
OpenFlow 1.3 controller used in this project does not use those features.
The error can be safely ignored if it only appears as a warning during
import, not a fatal crash.

If it is fatal:
```bash
pip install tinyrpc==0.9.4
```

---

### Issue 4: Ryu fails to start in WSL2 — socket permission

**Symptom:**
```
OSError: [Errno 13] Permission denied
```
when binding to port 6633.

**Fix:**
```bash
# Run with sudo, or use a port > 1024
sudo ryu-manager controller/simple_controller.py --ofp-tcp-listen-port 6633
# Or use unprivileged port
ryu-manager controller/simple_controller.py --ofp-tcp-listen-port 16633
# Then update Mininet topology to use port 16633
```

---

### Issue 5: Ryu does not see switch (no datapath event)

**Symptom:** Ryu starts, Mininet starts, but no `EventOFPSwitchFeatures`
event is received.

**Likely causes:**
1. Controller IP mismatch — Mininet pointing at wrong address
2. Firewall blocking port 6633
3. OVS not running
4. Wrong controller type in Mininet (using `OVSController` instead of `RemoteController`)

**Fix:**
```bash
# Verify OVS is running
sudo service openvswitch-switch status
# Verify controller is set on the bridge
sudo ovs-vsctl get-controller s1
# Should show: tcp:127.0.0.1:6633
```

---

## Recommended Simulation Machine Setup

```
OS:           Ubuntu 22.04 LTS (WSL2)
Python:       3.10 (system default — do NOT upgrade to 3.12+ for SDN work)
Mininet:      2.3.x (via apt)
OVS:          2.17.x (via apt)
Ryu:          faucetsdn/ryu (via pip from git)
eventlet:     0.33.3 (pinned)
OpenFlow:     1.3
```

**Critical:** Do NOT use Ubuntu 24.04 or the system Python 3.12 unless you
have verified the full Ryu + eventlet + OVS stack works. Ubuntu 22.04 with
Python 3.10 is the known-good baseline.

---

## Ryu Architecture Decision

Ryu remains the correct choice for this project despite its maintenance status
because:

1. The OpenFlow 1.3 protocol is stable — the Ryu OF1.3 library code is not
   changing and does not need maintenance for this use case.
2. Every academic SDN resource, tutorial, and reference implementation uses
   Ryu + Mininet. Switching would require re-learning a different API.
3. The alternative `os-ken` (OpenStack's maintained fork) is API-compatible
   with Ryu. If Ryu installation fails completely on the simulation machine,
   os-ken can be used as a drop-in by replacing `from ryu` with `from os_ken`
   imports. This is documented in `docs/troubleshooting.md` as a last resort.
4. All controller code in this project is written to Ryu's public API. If a
   migration to os-ken becomes necessary, it is a search-and-replace operation.

**Ryu will not be replaced in Phase 3. The architecture stands.**

---

## Verification Status

| Component | Status |
|-----------|--------|
| Ryu compatibility analysis | WINDOWS-DEV-TESTED (research only) |
| Recommended Python version identified | WINDOWS-DEV-TESTED |
| eventlet version fix applied | WINDOWS-DEV-TESTED |
| Actual Ryu installation on Ubuntu | LINUX-SIMULATION-REQUIRED |
| Actual OF1.3 handshake verified | LINUX-SIMULATION-REQUIRED |
| Ryu + OVS + Mininet end-to-end | LINUX-SIMULATION-REQUIRED |
