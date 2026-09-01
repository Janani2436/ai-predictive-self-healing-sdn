# Troubleshooting Guide

> All issues in this guide apply to the personal Ubuntu/WSL2 simulation machine
> unless explicitly labelled WINDOWS.

---

## Mininet Issues

### pingall fails (partial or complete)

**Symptom:** `pingall` shows dropped packets after topology start.

**Cause 1 — Ryu controller not running or not connected**
```bash
# Check Ryu is running in another terminal
ps aux | grep ryu-manager
# If not running, start it first:
ryu-manager controller/monitoring_controller.py
```

**Cause 2 — OVS not started**
```bash
sudo service openvswitch-switch start
sudo ovs-vsctl show   # should show bridges
```

**Cause 3 — Stale Mininet state from previous run**
```bash
sudo mn --clean
# Then restart topology
sudo python topology/campus_topology.py
```

**Cause 4 — Controller IP/port mismatch**
Check `config.yaml` controller host and port match what Ryu is listening on.

---

### Mininet fails to start: "Address already in use"

```bash
sudo mn --clean
sudo fuser -k 6633/tcp   # kill anything on OpenFlow port
```

---

### Mininet fails to start: "RTNETLINK answers: File exists"

Leftover interfaces from a previous crashed session:
```bash
sudo mn --clean
sudo ip link delete s1-eth1 2>/dev/null
# Repeat for all leftover interfaces listed in the error
```

---

### Hosts cannot communicate after link failure recovery

The controller may have stale flow rules. Clear all flows:
```bash
# From Mininet CLI
mininet> sh ovs-ofctl del-flows s1
# Repeat for each switch, or use cleanup.sh
bash scripts/cleanup.sh
```

---

## OVS Issues

### `ovs-vsctl show` returns empty or error

```bash
# Restart OVS
sudo service openvswitch-switch restart
sudo ovs-vsctl show
```

### OVS not available in WSL2

WSL2 may not support all OVS kernel modules. Check:
```bash
sudo modprobe openvswitch
dmesg | tail -20
```

If kernel module is unavailable, OVS userspace mode may be needed. See
the OVS WSL2 compatibility notes in `docs/setup.md`.

---

## Ryu Issues

### Ryu install fails: dependency conflicts

```bash
# Upgrade pip and setuptools first
pip install --upgrade pip setuptools

# Install eventlet FIRST at the pinned version
pip install "eventlet==0.33.3"

# Then install Ryu from faucetsdn fork
pip install git+https://github.com/faucetsdn/ryu.git
```

If the git install also fails:
```bash
pip install ryu==4.34
```

See `docs/ryu_compatibility.md` for full analysis.

### Ryu: "eventlet hub" errors / TypeError at startup

**Symptom:**
```
TypeError: cannot set 'is_timeout' attribute of immutable type 'TimeoutError'
```

**Cause:** eventlet version is too new. eventlet >= 0.35 breaks ryu 4.34.

**Fix:** Downgrade eventlet to the pinned version:
```bash
pip install "eventlet==0.33.3"
```

The `requirements-linux.txt` in this project pins `eventlet==0.33.3`.
If you installed with a different version, reinstall:
```bash
pip uninstall eventlet
pip install "eventlet==0.33.3"
```

### Ryu: "No module named 'ryu'"

The virtual environment is not activated:
```bash
source .venv/bin/activate
which ryu-manager  # should show path inside .venv
```

### Ryu: "OpenFlow connection failed" / no switch events

- Verify Mininet topology is running and controller IP/port are correct
- Check firewall: `sudo ufw status` — disable if blocking port 6633
- In WSL2, the controller may need to listen on `0.0.0.0` not `127.0.0.1`:
  ```bash
  # In config.yaml, set:
  controller:
    host: 0.0.0.0
    port: 6633
  ```
- Verify OVS controller is set:
  ```bash
  sudo ovs-vsctl get-controller s1
  # Should show: tcp:127.0.0.1:6633
  ```

### Ryu: "tinyrpc" import error

**Symptom:**
```
ImportError: cannot import name 'HTTPTransportFactory' from 'tinyrpc.transports'
```

**Cause:** Optional Ryu NETCONF/BGP features use tinyrpc. Only affects those
optional components — the OpenFlow 1.3 controller used here does not need them.

If it is a fatal crash (not just a warning):
```bash
pip install tinyrpc==0.9.4
```

### Ryu: port 6633 permission denied in WSL2

```bash
# Use sudo
sudo ryu-manager controller/simple_controller.py --ofp-tcp-listen-port 6633

# Or use an unprivileged port (>1024) and update config.yaml accordingly
ryu-manager controller/simple_controller.py --ofp-tcp-listen-port 16633
```

### os-ken as last-resort Ryu replacement

If Ryu cannot be installed at all, `os-ken` (OpenStack's maintained fork) is
API-compatible. Replace imports:
```python
# from ryu.base import app_manager         # original
from os_ken.base import app_manager        # os-ken drop-in

# from ryu.controller import ofp_event     # original
from os_ken.controller import ofp_event   # os-ken drop-in
```

Install:
```bash
pip install os-ken
```

All controller files in this project are written to the stable Ryu public API.
The switch to os-ken is a search-and-replace operation — confirm each import
before running. Only use this as a last resort after exhausting the Ryu options
in `docs/ryu_compatibility.md`.

---

## iperf3 Issues

### iperf3: "connect failed: Connection refused"

Server must be started before client:
```bash
# Terminal 1 (server side in Mininet)
mininet> H4 iperf3 -s &
# Terminal 2 (client)
mininet> H1 iperf3 -c 10.0.0.4 -t 30
```

### iperf3 not found

```bash
sudo apt-get install iperf3
```

---

## ML Issues (WINDOWS-COMPATIBLE)

### "No module named 'sklearn'"

```bash
# Windows
.venv\Scripts\activate
pip install -r requirements-dev.txt

# Ubuntu
source .venv/bin/activate
pip install -r requirements-linux.txt
```

### "Model file not found"

The model must be trained before running prediction:
```bash
python ml/train.py --dataset dataset/raw/synthetic_sample.csv
```

Note: training on synthetic data produces a model that is only suitable
for pipeline testing — not for real performance claims.

### Training fails: "Not enough samples"

The dataset is too small. Generate more data from Mininet experiments, or
for pipeline testing use the provided synthetic dataset generator.

---

## Git / Cross-Machine Issues

### Line ending problems (Windows ↔ Linux)

Configure git to handle line endings automatically:
```bash
# On Windows
git config core.autocrlf true

# On Ubuntu
git config core.autocrlf input
```

Or set in `.gitattributes` (already configured in this repository).

### Script fails on Ubuntu: "Permission denied"

```bash
chmod +x scripts/setup_linux.sh
chmod +x scripts/verify_linux_environment.sh
chmod +x scripts/run_demo.sh
chmod +x scripts/cleanup.sh
```

---

## WSL2-Specific Issues

### Mininet cannot create network interfaces in WSL2

WSL2 uses a custom kernel. Some versions lack full network namespace support.
Try:
```bash
# Check kernel version
uname -r
# Minimum recommended: 5.15+
```

If the kernel is too old, update WSL2:
```powershell
# Windows PowerShell (host)
wsl --update
```

### OVS kernel module unavailable in WSL2

Some WSL2 kernels do not include the OVS kernel module. A custom kernel
may be required. See:
https://github.com/microsoft/WSL/issues for current status.

Workaround: use OVS in userspace mode (slower but functional for emulation).

---

## Logging

All components log to stderr by default. To capture logs to file:

```bash
ryu-manager controller/monitoring_controller.py 2>&1 | tee logs/ryu.log
```

Log directory is git-ignored. Create it if needed:
```bash
mkdir -p logs
```
