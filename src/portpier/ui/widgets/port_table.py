"""The main port table. A DataTable subclass; one row per logical socket."""

from __future__ import annotations

from rich.text import Text
from textual.widgets import DataTable

from portpier.data.models import PortEntry
from portpier.ui.themes import state_color
from portpier.utils.format import bytes_to_human, format_cpu, seconds_to_uptime, truncate

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


def _right(value: str) -> Text:
    return Text(value, justify="right")


class PortTable(DataTable[Text]):
    """Renders ``PortEntry`` rows. STATE is colour-coded per the active theme."""

    DEFAULT_CSS = """
    PortTable {
        height: 1fr;
        width: 1fr;
    }
    """

    def __init__(self) -> None:
        super().__init__(zebra_stripes=True, cursor_type="row")
        self._entries: list[PortEntry] = []

    def on_mount(self) -> None:
        for key, label, width in _COLUMNS:
            self.add_column(label, key=key, width=width)

    def show_entries(self, entries: list[PortEntry]) -> None:
        """Replace all rows with ``entries`` (re-reads the active theme's colours)."""
        self._entries = entries
        self.clear()
        theme_name = self.app.theme
        for entry in entries:
            self.add_row(
                _right(str(entry.port)),
                Text(truncate(entry.process_name or "—", 14)),
                Text(truncate(entry.process_type or "—", 18)),
                _right(str(entry.pid) if entry.pid is not None else "—"),
                _right(bytes_to_human(entry.memory_rss_bytes)),
                _right(format_cpu(entry.cpu_percent)),
                Text(entry.state, style=state_color(theme_name, entry.state)),
                _right(seconds_to_uptime(entry.uptime_seconds)),
            )

    def refresh_colors(self) -> None:
        """Re-render rows so STATE colours follow a theme change."""
        self.show_entries(self._entries)
