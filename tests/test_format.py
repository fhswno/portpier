"""Tests for utils/format.py."""

from __future__ import annotations

from portpier.utils.format import bytes_to_human, format_cpu, seconds_to_uptime, truncate


def test_bytes_to_human() -> None:
    assert bytes_to_human(None) == "—"
    assert bytes_to_human(0) == "0 B"
    assert bytes_to_human(1_500) == "1.5 KB"
    assert bytes_to_human(128_000_000) == "128 MB"
    # rounds to 1000 KB → steps up to the next unit, then strips the .0
    assert bytes_to_human(999_999) == "1 MB"
    assert bytes_to_human(1_500_000_000) == "1.5 GB"


def test_seconds_to_uptime() -> None:
    assert seconds_to_uptime(None) == "—"
    assert seconds_to_uptime(45) == "45s"
    assert seconds_to_uptime(135) == "2m 15s"
    assert seconds_to_uptime(7_454) == "2h 4m"
    assert seconds_to_uptime(90_000) == "1d 1h"


def test_format_cpu() -> None:
    assert format_cpu(None) == "—"
    assert format_cpu(0.0) == "0%"
    assert format_cpu(2.0) == "2%"
    assert format_cpu(2.1) == "2.1%"
    assert format_cpu(100.0) == "100%"


def test_truncate() -> None:
    assert truncate("hello", 5) == "hello"  # exact length unchanged
    assert truncate("hello world", 5) == "hell…"  # over-length gets …
