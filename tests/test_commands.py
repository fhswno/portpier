"""Tests for the command-palette argument parsers (ui/commands.py).

These cover the pure parsing/clamping logic without instantiating a Textual app.
"""

from __future__ import annotations

from portpier.config import MAX_REFRESH, MIN_PORT_FLOOR, MIN_REFRESH
from portpier.ui.commands import parse_port_range, parse_refresh


def test_parse_refresh_basic() -> None:
    assert parse_refresh("refresh 5") == 5.0
    assert parse_refresh("refresh 0.5") == 0.5


def test_parse_refresh_clamps_to_range() -> None:
    assert parse_refresh("refresh 0.1") == MIN_REFRESH
    assert parse_refresh("refresh 999") == MAX_REFRESH


def test_parse_refresh_rejects_non_refresh() -> None:
    assert parse_refresh("theme dark") is None
    assert parse_refresh("refresh") is None
    assert parse_refresh("refresh abc") is None


def test_parse_refresh_is_case_insensitive_prefix() -> None:
    assert parse_refresh("Refresh 3") == 3.0


def test_parse_port_range_two_args() -> None:
    assert parse_port_range("port range 3000 4000") == (3000, 4000)


def test_parse_port_range_single_arg_defaults_max() -> None:
    assert parse_port_range("port range 3000") == (3000, 65535)


def test_parse_port_range_floors_min_to_1024() -> None:
    assert parse_port_range("port range 80 4000") == (MIN_PORT_FLOOR, 4000)


def test_parse_port_range_raises_max_below_min() -> None:
    assert parse_port_range("port range 4000 3000") == (4000, 4000)


def test_parse_port_range_tolerates_bare_port() -> None:
    assert parse_port_range("port 5000 6000") == (5000, 6000)


def test_parse_port_range_rejects_bad_input() -> None:
    assert parse_port_range("theme dark") is None
    assert parse_port_range("port range") is None
    assert parse_port_range("port range abc") is None
