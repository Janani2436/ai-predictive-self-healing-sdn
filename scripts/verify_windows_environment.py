"""
verify_windows_environment.py
WINDOWS-COMPATIBLE

Checks that the Windows development environment has all required
cross-platform dependencies installed. Reports Linux-only components
as NOT CHECKED / LINUX REQUIRED — it does not attempt to install or
verify Mininet, OVS, or Ryu on this machine.

Usage:
    python scripts/verify_windows_environment.py

Run this on the Windows work laptop only.
"""

import importlib
import shutil
import subprocess
import sys
from typing import Callable


# ── Colour helpers ────────────────────────────────────────────────────────────

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"


def _pass(msg: str) -> None:
    print(f"  {GREEN}[PASS]{RESET}    {msg}")


def _fail(msg: str) -> None:
    print(f"  {RED}[FAIL]{RESET}    {msg}")


def _warn(msg: str) -> None:
    print(f"  {YELLOW}[WARN]{RESET}    {msg}")


def _skip(msg: str) -> None:
    print(f"  {CYAN}[SKIP]{RESET}    {msg}  (NOT CHECKED / LINUX REQUIRED)")


def _section(title: str) -> None:
    print(f"\n{'-' * 60}")
    print(f"  {title}")
    print(f"{'-' * 60}")


# ── Individual checks ─────────────────────────────────────────────────────────

def check_python_version() -> bool:
    """Verify Python 3.10 or later is running."""
    major, minor = sys.version_info[:2]
    version_str = f"{major}.{minor}.{sys.version_info[2]}"
    if major == 3 and minor >= 10:
        _pass(f"Python {version_str}  ({sys.executable})")
        return True
    else:
        _fail(f"Python {version_str} — need 3.10+  ({sys.executable})")
        return False


def check_git() -> bool:
    """Verify Git is available on PATH."""
    git_path = shutil.which("git")
    if git_path is None:
        _fail("git not found on PATH")
        return False
    try:
        result = subprocess.run(
            ["git", "--version"],
            capture_output=True, text=True, timeout=10
        )
        _pass(result.stdout.strip())
        return True
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        _fail(f"git check failed: {exc}")
        return False


def check_pip() -> bool:
    """Verify pip is available."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "--version"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            _pass(result.stdout.strip())
            return True
        _fail("pip not available")
        return False
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        _fail(f"pip check failed: {exc}")
        return False


def check_python_package(package_name: str, import_name: str | None = None) -> bool:
    """Try to import a Python package and report its version if available."""
    import_name = import_name or package_name
    try:
        module = importlib.import_module(import_name)
        version = getattr(module, "__version__", "version unknown")
        _pass(f"{package_name}  {version}")
        return True
    except ImportError:
        _fail(f"{package_name} — not installed  (pip install {package_name})")
        return False


def check_linux_component(name: str, note: str = "") -> None:
    """Report a Linux-only component as skipped (not checked on Windows)."""
    suffix = f"  — {note}" if note else ""
    _skip(f"{name}{suffix}")


# ── Main verification ─────────────────────────────────────────────────────────

def main() -> int:
    """
    Run all environment checks and return an exit code.

    Returns:
        0 if all Windows-side checks pass, 1 if any fail.
    """
    print("\n" + "=" * 60)
    print("  AI-Driven Predictive Self-Healing SDN")
    print("  Windows Development Environment Verification")
    print("=" * 60)

    failures: list[str] = []

    # ── System tools ──────────────────────────────────────────────────────────
    _section("System Tools")
    if not check_python_version():
        failures.append("Python < 3.10")
    if not check_git():
        failures.append("git missing")
    if not check_pip():
        failures.append("pip missing")

    # ── Cross-platform runtime packages ───────────────────────────────────────
    _section("Cross-Platform Python Packages (requirements.txt)")

    runtime_packages: list[tuple[str, str]] = [
        ("numpy", "numpy"),
        ("pandas", "pandas"),
        ("scikit-learn", "sklearn"),
        ("joblib", "joblib"),
        ("networkx", "networkx"),
        ("matplotlib", "matplotlib"),
        ("python-dotenv", "dotenv"),
        ("PyYAML", "yaml"),
        ("tqdm", "tqdm"),
    ]

    for pkg_name, import_name in runtime_packages:
        if not check_python_package(pkg_name, import_name):
            failures.append(pkg_name)

    # ── Development / testing packages ────────────────────────────────────────
    _section("Development & Testing Packages (requirements-dev.txt)")

    dev_packages: list[tuple[str, str]] = [
        ("pytest", "pytest"),
        ("pytest-cov", "pytest_cov"),
    ]

    for pkg_name, import_name in dev_packages:
        if not check_python_package(pkg_name, import_name):
            failures.append(pkg_name)

    # ── Linux-only components (skipped on Windows) ────────────────────────────
    _section("Linux / SDN Components  (NOT CHECKED — LINUX REQUIRED)")

    check_linux_component("Mininet", "apt-get install mininet on Ubuntu")
    check_linux_component("Open vSwitch (OVS)", "apt-get install openvswitch-switch")
    check_linux_component("Ryu SDN Controller", "pip install ryu on Ubuntu")
    check_linux_component("OpenFlow 1.3 socket", "requires Linux kernel networking")
    check_linux_component("iperf3", "apt-get install iperf3 on Ubuntu")
    print(f"\n  Run  bash scripts/verify_linux_environment.sh  on Ubuntu to check these.")

    # ── Summary ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    if failures:
        print(f"  {RED}RESULT: {len(failures)} check(s) FAILED{RESET}")
        for item in failures:
            print(f"    - {item}")
        print()
        print("  Install missing packages with:")
        print("    pip install -r requirements-dev.txt")
        print("=" * 60 + "\n")
        return 1
    else:
        print(f"  {GREEN}RESULT: All Windows-side checks PASSED{RESET}")
        print()
        print("  Linux SDN components were skipped (not applicable on Windows).")
        print("  Verify those on the Ubuntu simulation machine.")
        print("=" * 60 + "\n")
        return 0


if __name__ == "__main__":
    sys.exit(main())
