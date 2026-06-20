"""The process-detail screen: extended info for a single socket's process.

Opened with Enter on a selected row; Esc or q pops back to the main screen with
the same row still selected (the main screen is only suspended, never rebuilt).

Detail data is fetched on mount in a worker thread (``collect_detail``); a
loading indicator shows until the result is ready. Missing/denied fields render
as a dash — never a crash.
"""

from __future__ import annotations

import asyncio

from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.css.query import NoMatches
from textual.screen import Screen
from textual.widgets import LoadingIndicator, Static

from portpier.data.collector import Collector
from portpier.data.models import DetailInfo, PortEntry
from portpier.ui.themes import TOKENS
from portpier.ui.widgets.kill_dialog import KillConfirmDialog
from portpier.utils.format import bytes_to_human, seconds_to_uptime

_PLACEHOLDER = "—"


def _text(value: str | None) -> str:
    return value if value is not None else _PLACEHOLDER


def _num(value: int | None) -> str:
    return _PLACEHOLDER if value is None else str(value)


def _pct(value: float | None) -> str:
    return _PLACEHOLDER if value is None else f"{value:.1f}%"


def _kv(pairs: list[tuple[str, str]]) -> list[str]:
    """Align ``label: value`` pairs to the widest label in the group."""
    width = max((len(label) for label, _ in pairs), default=0)
    return [f"{label + ':':<{width + 1}} {value}" for label, value in pairs]


def _conn_lines(conns: list[PortEntry]) -> list[str]:
    if not conns:
        return [_PLACEHOLDER]
    return [f"{c.port:<6} {c.state:<13} {c.remote_address or _PLACEHOLDER}" for c in conns]


def _env_lines(env: dict[str, str]) -> list[str]:
    if not env:
        return [_PLACEHOLDER]
    return [f"{key}={env[key]}" for key in sorted(env)]


def _fd_lines(fds: list[str]) -> list[str]:
    return list(fds) if fds else [_PLACEHOLDER]


def _parent_line(info: DetailInfo) -> str:
    if info.parent_name is not None and info.parent_pid is not None:
        return f"{info.parent_name} (PID {info.parent_pid})"
    if info.parent_name is not None:
        return info.parent_name
    if info.parent_pid is not None:
        return f"PID {info.parent_pid}"
    return _PLACEHOLDER


class DetailScreen(Screen[None]):
    """Full-screen process detail for a single port entry."""

    DEFAULT_CSS = """
    DetailScreen {
        background: $background;
    }
    #detail-title {
        dock: top;
        height: 1;
        background: $header-bg;
        color: $foreground;
        padding: 0 1;
    }
    #detail-content {
        height: 1fr;
    }
    #detail-footer {
        dock: bottom;
        height: 1;
        background: $panel;
        color: $text-muted;
        padding: 0 1;
    }
    #detail-loading-wrap {
        height: 1fr;
        content-align: center middle;
        text-align: center;
        color: $text-muted;
    }
    #detail-body {
        height: 1fr;
    }
    #detail-left, #detail-right {
        width: 1fr;
        height: 1fr;
        padding: 0 1;
        border: round $panel;
    }
    .detail-section {
        padding-bottom: 1;
    }
    """

    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back", show=True),
        Binding("q", "app.pop_screen", "Back", show=False),
        Binding("k", "kill", "Kill", show=False),
    ]

    def __init__(self, collector: Collector, pid: int, entry: PortEntry) -> None:
        super().__init__()
        # Plain values only — the table keeps refreshing behind this screen.
        self._collector = collector
        self._pid = pid
        self._entry = entry

    @property
    def _tokens(self) -> dict[str, str]:
        return TOKENS.get(self.app.theme, TOKENS["dark"])

    # -- layout --------------------------------------------------------------

    def compose(self) -> ComposeResult:
        tokens = self._tokens
        title = Text()
        title.append("← Back (Esc)", style=tokens["text-muted"])
        accent = f"bold {tokens['accent']}"
        title.append(f"    Process Detail — port {self._entry.port}", style=accent)
        footer = Text("[Esc] Back   ", style=tokens["text-muted"])
        footer.append("[k] Kill process", style=tokens["text-muted"])

        yield Static(title, id="detail-title")
        with Vertical(id="detail-content"):
            yield Container(LoadingIndicator(), id="detail-loading-wrap")
        yield Static(footer, id="detail-footer")

    def on_mount(self) -> None:
        self._fetch()

    # -- data fetch (off the UI thread) -------------------------------------

    @work(exclusive=True, group="detail")
    async def _fetch(self) -> None:
        info = await asyncio.to_thread(self._collector.collect_detail, self._pid, self._entry)
        self._populate(info)

    def _populate(self, info: DetailInfo) -> None:
        try:
            content = self.query_one("#detail-content", Vertical)
        except NoMatches:
            return  # screen was dismissed before the fetch completed
        content.remove_children()

        left_sections = [
            self._section("PROCESS INFO", self._process_info_lines(info)),
            self._section("COMMAND", [self._command_line(info)]),
            self._section("WORKING DIR", [_text(info.cwd)]),
            self._section("PARENT", [_parent_line(info)]),
            self._section("MEMORY", self._memory_lines(info)),
        ]
        right_sections = [
            self._section("CONNECTIONS", _conn_lines(info.all_connections)),
            self._section("OPEN FILE DESCRIPTORS (first 20)", _fd_lines(info.fd_sample)),
            self._section("ENVIRONMENT", _env_lines(info.env_vars)),
        ]

        left = VerticalScroll(*left_sections, id="detail-left")
        right = VerticalScroll(*right_sections, id="detail-right")
        content.mount(Horizontal(left, right, id="detail-body"))

    # -- section builders ----------------------------------------------------

    def _section(self, heading: str, lines: list[str]) -> Static:
        tokens = self._tokens
        text = Text()
        text.append(heading, style=f"bold {tokens['accent']}")
        text.append("\n")
        text.append("\n".join(lines))
        return Static(text, classes="detail-section")

    def _process_info_lines(self, info: DetailInfo) -> list[str]:
        entry = info.entry
        return _kv(
            [
                ("Name", _text(entry.process_name)),
                ("Type", _text(entry.process_type)),
                ("PID", _num(entry.pid)),
                ("User", _text(entry.user)),
                ("Status", _text(entry.status)),
                ("Uptime", seconds_to_uptime(entry.uptime_seconds)),
                ("Threads", _num(info.num_threads)),
                ("Open FDs", _num(info.num_fds)),
            ]
        )

    @staticmethod
    def _command_line(info: DetailInfo) -> str:
        return " ".join(info.cmdline) if info.cmdline else _PLACEHOLDER

    def _memory_lines(self, info: DetailInfo) -> list[str]:
        entry = info.entry
        return _kv(
            [
                ("RSS", bytes_to_human(entry.memory_rss_bytes)),
                ("VMS", bytes_to_human(info.memory_vms_bytes)),
                ("RAM%", _pct(info.memory_percent)),
            ]
        )

    # -- keybindings ---------------------------------------------------------

    def action_kill(self) -> None:
        self.app.push_screen(
            KillConfirmDialog(self._pid, self._entry.port, self._entry.process_name or "process"),
            self._on_kill_result,
        )

    def _on_kill_result(self, success: bool | None) -> None:
        # On a successful kill the process is gone — its detail is now stale, so
        # pop back to the main table. Failures and cancels leave the user here.
        if success:
            self.app.pop_screen()
