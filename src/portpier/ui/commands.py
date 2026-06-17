"""Command-palette provider for portpier.

A single :class:`Provider` powers the palette (``Ctrl+P``). It offers concrete
commands (``theme dark``, ``toggle pid``, ``sort cpu desc``, ...) and filters
them with Textual's fuzzy matcher. Commands that take an arbitrary numeric
argument (``refresh`` and ``port range``) additionally synthesize a hit from
the live query so any value works, not just presets.

Argument *parsing* lives in pure functions (``parse_refresh`` /
``parse_port_range``) so it can be unit-tested without a Textual app.
"""

from __future__ import annotations

from collections.abc import Callable
from functools import partial
from typing import TYPE_CHECKING, cast

from textual.command import DiscoveryHit, Hit, Hits, Provider

from portpier.config import MAX_REFRESH, MIN_PORT_FLOOR, MIN_REFRESH
from portpier.ui.themes import THEME_NAMES
from portpier.ui.widgets.port_table import COLUMN_KEYS
from portpier.ui.widgets.port_table import SORTABLE as _SORTABLE_SET

if TYPE_CHECKING:
    from portpier.app import PortpierApp

# Columns the user can sort by, in canonical order.
_SORTABLE: tuple[str, ...] = tuple(c for c in COLUMN_KEYS if c in _SORTABLE_SET)

# Everything toggleable except PORT (PORT is always visible).
_TOGGLEABLE: tuple[str, ...] = tuple(c for c in COLUMN_KEYS if c != "port")

# Sensible default direction per sort column (port asc; the rest high-first).
_SORT_DEFAULT_DESC: dict[str, bool] = {"port": False, "memory": True, "cpu": True, "uptime": True}

# Discoverable presets for numeric commands.
_REFRESH_PRESETS: tuple[float, ...] = (0.5, 1.0, 2.0, 5.0, 10.0, 30.0)
_PORT_RANGE_PRESETS: tuple[tuple[int, int], ...] = (
    (3000, 4000),
    (5173, 5173),
    (8000, 9000),
    (3000, 9999),
)

# A candidate command: (palette text, help text, callback).
_Candidate = tuple[str, str | None, Callable[[], object]]


def _fmt_num(value: float) -> str:
    """Compact number (2.0 -> "2", 0.5 -> "0.5")."""
    return f"{value:g}"


def _fmt_secs(value: float) -> str:
    return f"{value:g}s"


def _fmt_range(lo: int, hi: int) -> str:
    return f"port range {lo} {hi}" if lo != hi else f"port range {lo}"


def parse_refresh(query: str) -> float | None:
    """Parse ``refresh <seconds>`` and clamp to the valid range.

    Returns the clamped seconds, or ``None`` if the query isn't a refresh
    command or its argument isn't a number.
    """
    parts = query.strip().split()
    if len(parts) < 2 or parts[0].lower() != "refresh":
        return None
    try:
        value = float(parts[1])
    except ValueError:
        return None
    if value != value:  # NaN guard
        return None
    return max(MIN_REFRESH, min(value, MAX_REFRESH))


def parse_port_range(query: str) -> tuple[int, int] | None:
    """Parse ``port range <min> [max]`` (a bare ``port <min> [max]`` is tolerated).

    ``min`` is floored to ``MIN_PORT_FLOOR`` (1024). ``max`` defaults to 65535
    and is raised to ``min`` if smaller. Returns ``None`` on a missing or
    non-integer argument.
    """
    parts = query.strip().split()
    if not parts or parts[0].lower() != "port":
        return None
    rest = parts[1:]
    if rest and rest[0].lower() == "range":
        rest = rest[1:]
    nums: list[int] = []
    for token in rest[:2]:
        try:
            nums.append(int(token))
        except ValueError:
            return None
    if not nums:
        return None
    lo = max(nums[0], MIN_PORT_FLOOR)
    hi = nums[1] if len(nums) > 1 else 65535
    if hi < lo:
        hi = lo
    return (lo, hi)


class PortpierCommandProvider(Provider):
    """All portpier commands, surfaced in Textual's command palette."""

    # -- Provider API --------------------------------------------------------

    async def discover(self) -> Hits:
        app = self._app()
        by_text = {text: (text, help_text, cb) for text, help_text, cb in self._static(app)}
        # A curated, short default view: one representative command per group.
        curated = (
            "help",
            "theme dark",
            "toggle pid",
            "sort memory desc",
            "refresh 2",
            "port range 3000 9999",
        )
        for key in curated:
            if key in by_text:
                cmd_text, help_text, cb = by_text[key]
                yield DiscoveryHit(cmd_text, cb, text=cmd_text, help=help_text)

    async def search(self, query: str) -> Hits:
        q = query.strip()
        if not q:
            return
        app = self._app()
        candidates = self._static(app) + self._dynamic(app, q)
        matcher = self.matcher(q)
        for cmd_text, help_text, cb in candidates:
            score = matcher.match(cmd_text)
            if score > 0:
                yield Hit(score, matcher.highlight(cmd_text), cb, text=cmd_text, help=help_text)

    # -- candidate construction ---------------------------------------------

    def _app(self) -> PortpierApp:
        # Lazy import: a top-level import would be circular (app.py imports
        # this module for COMMANDS). At runtime the app module is already
        # loaded, so this resolves from sys.modules without re-execution.
        from portpier.app import PortpierApp as _PortpierApp

        return cast(_PortpierApp, self.app)

    def _static(self, app: PortpierApp) -> list[_Candidate]:
        out: list[_Candidate] = []
        for name in THEME_NAMES:
            out.append(
                (f"theme {name}", f"Switch to the {name} theme", partial(app.set_theme, name))
            )
        for col in _TOGGLEABLE:
            out.append(
                (
                    f"toggle {col}",
                    f"Show or hide the {col.upper()} column",
                    partial(app.apply_column_toggle, col),
                )
            )
        out.append(
            ("toggle port", "PORT is always visible", partial(app.apply_column_toggle, "port"))
        )
        for col in _SORTABLE:
            default_desc = _SORT_DEFAULT_DESC[col]
            word = "descending" if default_desc else "ascending"
            out.append(
                (
                    f"sort {col}",
                    f"Sort by {col.upper()} ({word})",
                    partial(app.apply_sort, col, default_desc),
                )
            )
            out.append(
                (
                    f"sort {col} asc",
                    f"Sort by {col.upper()} ascending",
                    partial(app.apply_sort, col, False),
                )
            )
            out.append(
                (
                    f"sort {col} desc",
                    f"Sort by {col.upper()} descending",
                    partial(app.apply_sort, col, True),
                )
            )
        for secs in _REFRESH_PRESETS:
            out.append(
                (
                    f"refresh {_fmt_num(secs)}",
                    f"Refresh every {_fmt_secs(secs)}",
                    partial(app.apply_refresh_interval, secs),
                )
            )
        for lo, hi in _PORT_RANGE_PRESETS:
            out.append(
                (
                    _fmt_range(lo, hi),
                    f"Only show ports {lo}-{hi}",
                    partial(app.apply_port_range, lo, hi),
                )
            )
        out.append(
            (
                "port range reset",
                "Clear the port range filter (1024-65535)",
                partial(app.apply_port_range, MIN_PORT_FLOOR, 65535),
            )
        )
        out.append(("help", "Show all commands", app.open_help))
        return out

    def _dynamic(self, app: PortpierApp, query: str) -> list[_Candidate]:
        """Synthesize a hit for arbitrary numeric arguments not in the presets."""
        out: list[_Candidate] = []
        secs = parse_refresh(query)
        if secs is not None and secs not in _REFRESH_PRESETS:
            out.append(
                (
                    f"refresh {_fmt_num(secs)}",
                    f"Refresh every {_fmt_secs(secs)}",
                    partial(app.apply_refresh_interval, secs),
                )
            )
        rng = parse_port_range(query)
        if rng is not None and rng not in _PORT_RANGE_PRESETS:
            lo, hi = rng
            out.append(
                (
                    _fmt_range(lo, hi),
                    f"Only show ports {lo}-{hi}",
                    partial(app.apply_port_range, lo, hi),
                )
            )
        return out
