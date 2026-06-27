"""The main port table. A DataTable subclass; one row per logical socket.

Routine refreshes update cells in place (no clear()) so the view never flickers
or loses its scroll position. A full rebuild happens only on user-driven changes
(sort, filter, theme), where preserving scroll/cursor is cheap and one-off.
"""

from __future__ import annotations

from contextlib import suppress

from rich.text import Text
from textual.binding import Binding
from textual.message import Message
from textual.widgets import DataTable
from textual.widgets.data_table import CellDoesNotExist, RowDoesNotExist

from portpier.data.models import PortEntry
from portpier.ui.themes import state_color
from portpier.utils.format import bytes_to_human, format_cpu, seconds_to_uptime, truncate

# (key, label, width). PORT is always present and non-toggleable.
_COLUMNS: list[tuple[str, str, int]] = [
    ("port", "PORT", 7),
    ("process", "PROCESS", 14),
    ("type", "TYPE", 18),
    ("pid", "PID", 8),
    ("memory", "MEMORY", 12),
    ("cpu", "CPU%", 8),
    ("state", "STATE", 13),
    ("uptime", "UPTIME", 12),
]

# Canonical column order, for config + visibility rebuilds.
COLUMN_KEYS: list[str] = [key for key, _, _ in _COLUMNS]

# Columns the user can sort by. Others rely on search/filter instead.
SORTABLE = frozenset({"port", "memory", "cpu", "uptime"})

# Cells whose values change between refreshes (the rest are fixed per row key).
_VOLATILE_COLUMNS = ("memory", "cpu", "uptime")


def _right(value: str) -> Text:
    return Text(value, justify="right")


def _row_key(entry: PortEntry) -> str:
    """Stable identity for a socket, matching the collector's dedup key."""
    remote = entry.remote_address or ""
    return f"{entry.protocol}|{entry.local_address}|{entry.port}|{remote}|{entry.state}"


class PortTable(DataTable[Text]):
    """Renders PortEntry rows; STATE colour-coded; click-to-sort headers."""

    DEFAULT_CSS = """
    PortTable {
        height: 1fr;
        width: 1fr;
        /* macOS draws iTerm2's overlay scrollbar at the window edge when
           "Show scroll bars: Always" is set — on top of ours, so two bars
           appeared (and overlapped into a split look). Hide ours; the OS one
           remains. To use our themed scrollbar instead, set macOS
           "Show scroll bars: When scrolling" and change this to 1. */
        scrollbar-size-vertical: 0;
    }
    """

    BINDINGS = [
        Binding("/", "request_search", "Search", show=False),
        Binding("s", "cycle_sort", "Sort", show=False),
        Binding("enter", "request_detail", "Details", show=False),
        Binding("k", "request_kill", "Kill", show=False),
    ]

    class SearchRequested(Message):
        """Posted when the user presses `/` to jump to the search box."""

    class SortRequested(Message):
        """Posted when the user presses `s` to cycle the sort column."""

    class DetailRequested(Message):
        """Posted when the user presses Enter to open the detail view."""

    class KillRequested(Message):
        """Posted when the user presses `k` to kill the selected process."""

    def __init__(self) -> None:
        super().__init__(zebra_stripes=True, cursor_type="row")
        self._entries: list[PortEntry] = []
        self._sort_key = "port"
        self._sort_descending = False
        self._row_order: list[str] = []
        # Columns currently rendered. PORT is always present. Toggled via the
        # command palette (apply_columns); stored as a set for O(1) cell checks.
        self._visible: set[str] = set(COLUMN_KEYS)

    def on_mount(self) -> None:
        self._add_columns()

    def resort(self, entries: list[PortEntry], sort_key: str, descending: bool) -> None:
        """Full rebuild in the given order. For user actions (sort/filter) and
        the first load. ``clear()`` leaves the view at the top, which is exactly
        where you want to land after a sort or a new filter — no scroll restore,
        so there's no flash-to-top-then-back."""
        indicator_changed = sort_key != self._sort_key or descending != self._sort_descending
        self._entries = entries
        self._sort_key = sort_key
        self._sort_descending = descending

        if indicator_changed or not self.columns:
            self.clear(columns=True)
            self._add_columns()
        else:
            self.clear()
        for entry in entries:
            self._add_row(entry)
        self._row_order = [_row_key(e) for e in entries]

    def sync(self, entries: list[PortEntry]) -> None:
        """Incremental update for routine refreshes: update surviving rows in
        place, drop gone rows, append new ones. No clear() -> the scroll
        position and cursor stay put and nothing flickers."""
        self._entries = entries
        desired = {_row_key(e): e for e in entries}
        cursor_key = self._cursor_key()

        survivors = [k for k in self._row_order if k in desired]
        for key in self._row_order:
            if key not in desired:
                self._safe_remove(key)
        for key in survivors:
            self._update_volatile_cells(key, desired[key])

        existing = set(survivors)
        for key, entry in desired.items():
            if key not in existing:
                self._add_row(entry)
                survivors.append(key)

        self._row_order = survivors
        self._restore_cursor(cursor_key)

    def refresh_colors(self) -> None:
        """Recolour STATE cells in place after a theme change (no rebuild, so
        the scroll position is untouched)."""
        if "state" not in self._visible:
            return
        theme_name = self.app.theme
        for entry in self._entries:
            with suppress(CellDoesNotExist):
                self.update_cell(
                    _row_key(entry),
                    "state",
                    Text(entry.state, style=state_color(theme_name, entry.state)),
                    update_width=False,
                )

    def apply_columns(self, visible: list[str] | set[str]) -> None:
        """Rebuild the table showing only ``visible`` columns (PORT forced on).

        A full rebuild (columns + rows) is required because DataTable's column
        set is fixed once rows reference it; toggling must re-add columns and
        re-emit every row with the matching cell arity.
        """
        self._visible = set(visible) | {"port"}
        self.clear(columns=True)
        self._add_columns()
        for entry in self._entries:
            self._add_row(entry)
        self._row_order = [_row_key(e) for e in self._entries]

    def action_request_search(self) -> None:
        self.post_message(self.SearchRequested())

    def action_cycle_sort(self) -> None:
        self.post_message(self.SortRequested())

    def action_request_detail(self) -> None:
        self.post_message(self.DetailRequested())

    def action_request_kill(self) -> None:
        self.post_message(self.KillRequested())

    def selected_entry(self) -> PortEntry | None:
        """Resolve the PortEntry under the cursor, or None if no row is selected.

        Goes through ``_row_order`` (display order) rather than ``_entries``
        because :meth:`sync` preserves the previous display order across
        refreshes — the two lists hold the same keys in different orders.
        """
        if self.row_count == 0:
            return None
        row, _ = self.cursor_coordinate
        if row < 0 or row >= len(self._row_order):
            return None
        key = self._row_order[row]
        for entry in self._entries:
            if _row_key(entry) == key:
                return entry
        return None

    # -- internals -----------------------------------------------------------

    def _add_columns(self) -> None:
        for key, label, width in _COLUMNS:
            if key not in self._visible:
                continue
            header: str | Text = label
            if key == self._sort_key and key in SORTABLE:
                header = f"{label} {'▼' if self._sort_descending else '▲'}"
            self.add_column(header, key=key, width=width)

    def _cell_for(self, entry: PortEntry, key: str) -> Text:
        if key == "port":
            return _right(str(entry.port))
        if key == "process":
            return Text(truncate(entry.process_name or "—", 14))
        if key == "type":
            return Text(truncate(entry.process_type or "—", 18))
        if key == "pid":
            return _right(str(entry.pid) if entry.pid is not None else "—")
        if key == "memory":
            return _right(bytes_to_human(entry.memory_rss_bytes))
        if key == "cpu":
            return _right(format_cpu(entry.cpu_percent))
        if key == "state":
            return Text(entry.state, style=state_color(self.app.theme, entry.state))
        # uptime
        return _right(seconds_to_uptime(entry.uptime_seconds))

    def _add_row(self, entry: PortEntry) -> None:
        cells = [self._cell_for(entry, key) for key, _, _ in _COLUMNS if key in self._visible]
        self.add_row(*cells, key=_row_key(entry))

    def _update_volatile_cells(self, key: str, entry: PortEntry) -> None:
        for column in _VOLATILE_COLUMNS:
            if column not in self._visible:
                continue
            self.update_cell(key, column, self._cell_for(entry, column), update_width=False)

    def _safe_remove(self, key: str) -> None:
        with suppress(RowDoesNotExist):
            self.remove_row(key)

    def _cursor_key(self) -> str | None:
        if self.row_count == 0:
            return None
        row, _ = self.cursor_coordinate
        if row < 0 or row >= self.row_count:
            return None
        return self.coordinate_to_cell_key(self.cursor_coordinate).row_key.value

    def _restore_cursor(self, key: str | None) -> None:
        if key is None:
            return
        try:
            index = self.get_row_index(key)
        except RowDoesNotExist:
            return
        # scroll=False so cursor restoration doesn't move the viewport.
        self.move_cursor(row=index, scroll=False)
