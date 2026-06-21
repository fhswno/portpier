"""The live dashboard screen: polling, sorting, and live search."""

from __future__ import annotations

import asyncio

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.timer import Timer
from textual.widgets import DataTable, Input, Static

from portpier.data.collector import Collector
from portpier.data.models import PortEntry
from portpier.ui.screens.detail import DetailScreen
from portpier.ui.widgets.header import StatusHeader
from portpier.ui.widgets.kill_dialog import KillConfirmDialog
from portpier.ui.widgets.port_table import SORTABLE, PortTable
from portpier.ui.widgets.search_bar import SearchBar
from portpier.utils.format import bytes_to_human

# Keyboard sort cycle (column, descending) — sensible default direction per column.
_SORT_CYCLE: list[tuple[str, bool]] = [
    ("port", False),
    ("memory", True),
    ("cpu", True),
    ("uptime", True),
]


class MainScreen(Screen[None]):
    DEFAULT_CSS = """
    MainScreen {
        background: $background;
        /* The PortTable is the only scroller; the screen itself never scrolls
           (prevents a second, outer scrollbar). */
        overflow: hidden hidden;
    }
    #empty-state {
        height: 1fr;
        width: 1fr;
        color: $text-muted;
        content-align: center middle;
        text-align: center;
        display: none;
    }
    """

    BINDINGS = [
        Binding("escape", "clear_search", "Clear search", show=False),
        Binding("r", "force_refresh", "Refresh", show=False),
    ]

    def __init__(
        self,
        collector: Collector,
        *,
        min_port: int,
        max_port: int,
        refresh_interval: float,
        sort_column: str,
        sort_order: str,
        columns: list[str],
    ) -> None:
        super().__init__()
        self._collector = collector
        self._min_port = min_port
        self._max_port = max_port
        self._refresh_interval = refresh_interval
        self._entries: list[PortEntry] = []
        self._sort_key = sort_column if sort_column in SORTABLE else "port"
        self._sort_descending = sort_order == "desc"
        self._columns = columns
        self._query = ""
        self._first_render = True
        self._timer: Timer | None = None

    def compose(self) -> ComposeResult:
        yield StatusHeader()
        yield PortTable()
        yield Static("", id="empty-state")
        yield SearchBar()

    def on_mount(self) -> None:
        header = self.query_one(StatusHeader)
        header.theme_name = self.app.theme
        header.refresh_interval = self._refresh_interval
        # Apply persisted column visibility before the first render.
        self.query_one(PortTable).apply_columns(self._columns)
        self.query_one(PortTable).focus()
        # Collect once immediately, then on the configured cadence.
        self._tick()
        self._timer = self.set_interval(self._refresh_interval, self._tick)

    def _tick(self) -> None:
        self.collect_ports()

    @work(exclusive=True, group="refresh")
    async def collect_ports(self) -> None:
        """Run the (blocking) psutil scan off the UI thread, then apply it."""
        entries = await asyncio.to_thread(
            self._collector.collect_ports, self._min_port, self._max_port
        )
        self._entries = entries
        view = self._compute_view()
        table = self.query_one(PortTable)
        if self._first_render:
            table.resort(view, self._sort_key, self._sort_descending)
            self._first_render = False
        else:
            # Routine refresh: incremental, in-place — no flicker, scroll stays.
            table.sync(view)
        self._update_header(view)
        self.query_one(StatusHeader).sudo_warning = self._collector.access_denied
        self._apply_empty_state(view)
        self.query_one(StatusHeader).pulse()

    # -- view derivation (no psutil calls) -----------------------------------

    def _compute_view(self) -> list[PortEntry]:
        view = [e for e in self._entries if _matches(e, self._query)]
        view.sort(key=lambda e: _sort_value(e, self._sort_key), reverse=self._sort_descending)
        return view

    def _rerender_now(self) -> None:
        """Apply a user-driven change (sort/filter) immediately with a full,
        ordered rebuild rather than waiting for the next refresh tick."""
        view = self._compute_view()
        self.query_one(PortTable).resort(view, self._sort_key, self._sort_descending)
        self._update_header(view)
        self._apply_empty_state(view)

    def _update_header(self, view: list[PortEntry]) -> None:
        header = self.query_one(StatusHeader)
        header.port_count = len(view)
        header.total_memory = bytes_to_human(_total_rss(view))
        self.query_one(SearchBar).set_status(self._query, len(view), len(self._entries))

    def _apply_empty_state(self, view: list[PortEntry]) -> None:
        """Swap between the table and the centered empty-state message.

        A display swap (rather than an overlay) keeps focus/layout simple:
        exactly one of the two is shown. On the empty->non-empty transition we
        refocus the table — but only if the user isn't actively typing a search.
        """
        table = self.query_one(PortTable)
        empty = self.query_one("#empty-state", Static)
        if view:
            was_hidden = not table.display
            table.display = True
            empty.display = False
            if was_hidden and not self.query_one("#search-input", Input).has_focus:
                table.focus()
        else:
            table.display = False
            empty.display = True
            empty.update(self._empty_message())

    def _empty_message(self) -> str:
        if not self._entries:
            return f"No processes found on ports {self._min_port}–{self._max_port}"
        return f'No matches for "{self._query}"'

    # -- command-palette-driven state changes --------------------------------

    def set_sort(self, column: str, descending: bool) -> None:
        """Apply a new sort (column + direction) and rebuild the view."""
        self._sort_key = column if column in SORTABLE else "port"
        self._sort_descending = descending
        self._rerender_now()

    def set_refresh_interval(self, seconds: float) -> None:
        """Restart the polling cadence at ``seconds`` and update the header."""
        self._refresh_interval = seconds
        if self._timer is not None:
            self._timer.stop()
        self._timer = self.set_interval(seconds, self._tick)
        self.query_one(StatusHeader).refresh_interval = seconds

    def set_port_range(self, min_port: int, max_port: int) -> None:
        """Update the scan range and trigger an immediate refresh."""
        self._min_port = min_port
        self._max_port = max_port
        self.collect_ports()

    def set_column_visibility(self, visible: list[str]) -> None:
        """Rebuild the table with the given columns (PORT always kept)."""
        self.query_one(PortTable).apply_columns(visible)

    # -- interaction ---------------------------------------------------------

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "search-input":
            self._query = event.value
            self._rerender_now()

    def on_data_table_header_selected(self, event: DataTable.HeaderSelected) -> None:
        key = event.column_key.value
        if key is None or key not in SORTABLE:
            return
        if key == self._sort_key:
            self._sort_descending = not self._sort_descending
        else:
            self._sort_key = key
            self._sort_descending = False
        self._rerender_now()

    def on_port_table_search_requested(self, event: PortTable.SearchRequested) -> None:
        self.query_one("#search-input", Input).focus()

    def on_port_table_sort_requested(self, event: PortTable.SortRequested) -> None:
        # Keyboard sort: cycle through useful (column, descending) states.
        current = (self._sort_key, self._sort_descending)
        index = _SORT_CYCLE.index(current) if current in _SORT_CYCLE else -1
        self._sort_key, self._sort_descending = _SORT_CYCLE[(index + 1) % len(_SORT_CYCLE)]
        self._rerender_now()

    def on_port_table_detail_requested(self, event: PortTable.DetailRequested) -> None:
        entry = self.query_one(PortTable).selected_entry()
        if entry is not None and entry.pid is not None:
            self.app.push_screen(DetailScreen(self._collector, entry.pid, entry))

    def on_port_table_kill_requested(self, event: PortTable.KillRequested) -> None:
        entry = self.query_one(PortTable).selected_entry()
        if entry is not None and entry.pid is not None:
            # Plain values only — the table keeps refreshing behind the modal.
            self.app.push_screen(
                KillConfirmDialog(entry.pid, entry.port, entry.process_name or "process")
            )

    def action_clear_search(self) -> None:
        # Clearing the value fires Input.Changed, which re-renders unfiltered.
        self.query_one("#search-input", Input).value = ""
        self.query_one(PortTable).focus()

    def action_force_refresh(self) -> None:
        # Manual, immediate rescan (the table still refreshes on its interval too).
        self.collect_ports()


def _matches(entry: PortEntry, query: str) -> bool:
    if not query:
        return True
    needle = query.lower()
    fields = (
        str(entry.port),
        entry.process_name or "",
        entry.process_type or "",
        entry.state,
        str(entry.pid) if entry.pid is not None else "",
    )
    return any(needle in field.lower() for field in fields)


def _sort_value(entry: PortEntry, key: str) -> float:
    if key == "memory":
        return float(entry.memory_rss_bytes) if entry.memory_rss_bytes is not None else -1.0
    if key == "cpu":
        return entry.cpu_percent if entry.cpu_percent is not None else -1.0
    if key == "uptime":
        return entry.uptime_seconds if entry.uptime_seconds is not None else -1.0
    return float(entry.port)


def _total_rss(entries: list[PortEntry]) -> int:
    """Sum RSS once per process. A PID with many sockets must not be counted
    once per socket, which would massively inflate the total."""
    total = 0
    counted: set[int] = set()
    for entry in entries:
        if entry.pid is not None:
            if entry.pid in counted:
                continue
            counted.add(entry.pid)
        total += entry.memory_rss_bytes or 0
    return total
