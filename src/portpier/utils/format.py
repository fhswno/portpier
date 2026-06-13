"""Pure formatting helpers for the UI layer. No I/O, no side effects."""

from __future__ import annotations

_BYTE_UNITS = ["B", "KB", "MB", "GB", "TB", "PB"]
_PLACEHOLDER = "—"


def bytes_to_human(n: int | None) -> str:
    """Convert a byte count to a human-readable string using 1000-based units.

    ``None`` → ``"—"``, ``0`` → ``"0 B"``. Trailing ``.0`` is stripped so whole
    numbers render without a decimal. After rounding to one decimal, a value
    that reaches 1000 steps up to the next unit (so 999_999 → "1 MB").
    """
    if n is None:
        return _PLACEHOLDER
    if n == 0:
        return "0 B"
    value = float(n)
    idx = 0
    while idx < len(_BYTE_UNITS) - 1 and round(value, 1) >= 1000:
        value /= 1000
        idx += 1
    formatted = f"{value:.1f}".rstrip("0").rstrip(".")
    return f"{formatted} {_BYTE_UNITS[idx]}"


def seconds_to_uptime(seconds: float | None) -> str:
    """Convert elapsed seconds to a compact uptime string.

    ``None`` → ``"—"``. Examples: 45 → "45s", 135 → "2m 15s", 7454 → "2h 4m",
    90000 → "1d 1h". The two largest non-zero units are shown.
    """
    if seconds is None:
        return _PLACEHOLDER
    total = max(int(seconds), 0)
    days, rem = divmod(total, 86_400)
    hours, rem = divmod(rem, 3_600)
    minutes, secs = divmod(rem, 60)
    if days > 0:
        return f"{days}d {hours}h"
    if hours > 0:
        return f"{hours}h {minutes}m"
    if minutes > 0:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def format_cpu(percent: float | None) -> str:
    """Format a CPU percentage with one decimal place, stripping a trailing .0.

    ``None`` → ``"—"``. Examples: 2.1 → "2.1%", 2.0 → "2%", 0.0 → "0%",
    100.0 → "100%".
    """
    if percent is None:
        return _PLACEHOLDER
    return f"{percent:.1f}".rstrip("0").rstrip(".") + "%"


def truncate(s: str, max_len: int) -> str:
    """Truncate ``s`` to ``max_len`` characters, appending '…' if truncated."""
    if len(s) <= max_len:
        return s
    if max_len <= 0:
        return ""
    return s[: max_len - 1] + "…"
