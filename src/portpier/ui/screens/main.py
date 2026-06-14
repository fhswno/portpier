"""The live dashboard screen. Polls the collector off-thread on a timer."""

from __future__ import annotations

import asyncio

from textual import work
from textual.app import ComposeResult
from textual.screen import Screen

from portpier.data.collector import Collector
from portpier.data.models import PortEntry
from portpier.ui.widgets.header import StatusHeader
from portpier.ui.widgets.port_table import PortTable
from portpier.ui.widgets.search_bar import SearchBar
from portpier.utils.format import bytes_to_human


class MainScreen(Screen[None]):
    DEFAULT_CSS = """
    MainScreen {
        background: $background;
    }
    """

    def __init__(
        self,
        collector: Collector,
        *,
        min_port: int,
        max_port: int,
        refresh_interval: float,
    ) -> None:
        super().__init__()
        self._collector = collector
        self._min_port = min_port
        self._max_port = max_port
        self._refresh_interval = refresh_interval

    def compose(self) -> ComposeResult:
        yield StatusHeader()
        yield PortTable()
        yield SearchBar()

    def on_mount(self) -> None:
        header = self.query_one(StatusHeader)
        header.theme_name = self.app.theme
        header.refresh_interval = self._refresh_interval
        self._tick()
        self.set_interval(self._refresh_interval, self._tick)

    def _tick(self) -> None:
        self.collect_ports()

    @work(exclusive=True, group="refresh")
    async def collect_ports(self) -> None:
        """Run the (blocking) psutil scan off the UI thread, then apply it."""
        entries = await asyncio.to_thread(
            self._collector.collect_ports, self._min_port, self._max_port
        )
        self._apply(entries)

    def _apply(self, entries: list[PortEntry]) -> None:
        self.query_one(PortTable).show_entries(entries)
        header = self.query_one(StatusHeader)
        header.port_count = len(entries)
        header.total_memory = bytes_to_human(_total_rss(entries))
        header.pulse()


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
