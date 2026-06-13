"""The live dashboard screen. Phase 2 renders hardcoded mock data."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import Screen

from portpier.data.models import PortEntry
from portpier.ui.widgets.header import StatusHeader
from portpier.ui.widgets.port_table import PortTable
from portpier.ui.widgets.search_bar import SearchBar
from portpier.utils.format import bytes_to_human

MOCK_ENTRIES: list[PortEntry] = [
    PortEntry(
        port=3000, protocol="TCP", state="LISTEN", local_address="0.0.0.0",
        remote_address=None, pid=81234, process_name="node", process_type="Node.js",
        memory_rss_bytes=128_000_000, cpu_percent=2.1, uptime_seconds=8054.0,
        user="dave", status="sleeping",
    ),
    PortEntry(
        port=8000, protocol="TCP", state="ESTABLISHED", local_address="127.0.0.1",
        remote_address="192.168.1.5:52341", pid=90123, process_name="python3",
        process_type="Python", memory_rss_bytes=96_000_000, cpu_percent=0.4,
        uptime_seconds=2712.0, user="dave", status="running",
    ),
    PortEntry(
        port=5432, protocol="TCP", state="TIME_WAIT", local_address="127.0.0.1",
        remote_address="10.0.0.2:54110", pid=4567, process_name="postgres",
        process_type="PostgreSQL", memory_rss_bytes=200_000_000, cpu_percent=0.1,
        uptime_seconds=262_800.0, user="postgres", status="sleeping",
    ),
    PortEntry(
        port=6379, protocol="TCP", state="CLOSE_WAIT", local_address="127.0.0.1",
        remote_address="10.0.0.5:8080", pid=7788, process_name="redis-server",
        process_type="Redis", memory_rss_bytes=64_000_000, cpu_percent=0.0,
        uptime_seconds=5400.0, user="dave", status="sleeping",
    ),
    PortEntry(
        port=9229, protocol="TCP", state="SYN_SENT", local_address="127.0.0.1",
        remote_address="172.16.0.9:6000", pid=81240, process_name="node",
        process_type="Node.js", memory_rss_bytes=24_000_000, cpu_percent=5.3,
        uptime_seconds=35.0, user="dave", status="running",
    ),
]


class MainScreen(Screen[None]):
    DEFAULT_CSS = """
    MainScreen {
        background: $background;
    }
    """

    def compose(self) -> ComposeResult:
        yield StatusHeader()
        yield PortTable()
        yield SearchBar()

    def on_mount(self) -> None:
        header = self.query_one(StatusHeader)
        header.port_count = len(MOCK_ENTRIES)
        header.total_memory = bytes_to_human(
            sum(e.memory_rss_bytes or 0 for e in MOCK_ENTRIES)
        )
        header.theme_name = self.app.theme
        self.query_one(PortTable).show_entries(MOCK_ENTRIES)
