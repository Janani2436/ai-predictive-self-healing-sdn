---
inclusion: always
---

# Coding Standards

## Language
Python 3.10+ compatible syntax. The development machine runs Python 3.14.
All code must be compatible with Python 3.10 minimum for portability to the
Ubuntu simulation machine.

## Style
- Follow PEP 8
- Maximum line length: 100 characters
- Use 4-space indentation (no tabs)
- One blank line between methods, two between top-level definitions

## Naming
- Variables and functions: snake_case
- Classes: PascalCase
- Constants: UPPER_SNAKE_CASE
- Private helpers: _leading_underscore
- No single-letter variable names except loop counters (i, j, k) and
  well-understood math (x, y)

## Type Hints
Use type hints on all public function signatures.

```python
def calculate_health_score(delay_ms: float, loss_pct: float, utilization_pct: float) -> float:
    ...
```

Internal helpers may omit hints where the type is obvious from context.

## Docstrings
Every module, class, and public function must have a docstring.

```python
def calculate_health_score(delay_ms: float, loss_pct: float, utilization_pct: float) -> float:
    """
    Calculate a composite health/cost score for a network link.

    Lower score = healthier link.

    Args:
        delay_ms: One-way delay in milliseconds.
        loss_pct: Packet loss percentage (0-100).
        utilization_pct: Link utilization percentage (0-100).

    Returns:
        Float health score. Higher value = worse condition.
    """
```

## Logging
Use Python's standard logging module. Never use bare print() in production code
(scripts and demos may use print() for human-readable output only).

Always use module-level loggers:
```python
import logging
logger = logging.getLogger(__name__)
```

Use structured prefixes in log messages:
- [MONITOR] — monitoring and statistics collection
- [PREDICTION] — ML inference results
- [OPTIMIZER] — path selection decisions
- [RYU] — controller actions
- [OPENFLOW] — flow rule installation
- [EXPERIMENT] — experiment lifecycle events
- [SELF-HEALING] — rerouting and recovery events

Log levels:
- DEBUG: detailed internal state
- INFO: normal operation milestones
- WARNING: degraded but recoverable conditions
- ERROR: failures requiring attention
- CRITICAL: system cannot continue

## Error Handling
All external operations (file I/O, network calls, model loading) must be wrapped
in try/except with specific exception types. Never use bare `except:`.

Provide actionable error messages:
```python
# Bad
except Exception:
    pass

# Good
except FileNotFoundError as exc:
    logger.error("[ML] Model file not found at %s. Run ml/train.py first.", model_path)
    raise
```

Never silently substitute fake data when real data is unavailable. Raise or log
a clear error instead.

## Configuration
No magic numbers. All thresholds, weights, ports, IPs, and durations must come
from a config object or environment variable.

```python
# Bad
if utilization > 85:

# Good
if utilization > config.congestion_threshold_pct:
```

## Modules
- Keep files small and focused (single responsibility)
- Maximum ~300 lines per module; split if larger
- No circular imports
- All packages must have __init__.py

## Testing
- Unit tests go in tests/
- Test files named test_<module>.py
- Test functions named test_<what>_<condition>()
- Use pytest
- Use controlled synthetic data — never real network data in unit tests
- Clearly mark synthetic data with comments

## Platform Separation
Mark code that requires Linux/Mininet with a module-level comment:

```python
# LINUX-SIMULATION-REQUIRED
# This module requires Mininet and Open vSwitch running on Ubuntu.
# It cannot be executed on the Windows development machine.
```

Mark Windows-safe code with:

```python
# WINDOWS-COMPATIBLE
# This module has no Linux networking dependencies and can be
# developed and unit-tested on the Windows development machine.
```

## Dependencies
- Only import from requirements.txt / requirements-linux.txt
- Do not introduce new packages without updating requirements files
- Do not use TensorFlow or PyTorch
- Do not use deep learning frameworks
- Prefer standard library where sufficient

## File Headers
Every source file should begin with a brief module docstring explaining its
purpose, platform requirements, and any important caveats.
