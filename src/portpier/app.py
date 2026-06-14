"""The root Textual application."""

from __future__ import annotations

from textual.app import App
from textual.binding import Binding

from portpier.config import load
from portpier.data.collector import Collector
from portpier.ui.screens.main import MainScreen
from portpier.ui.themes import THEME_NAMES, THEMES
from portpier.ui.widgets.header import StatusHeader
from portpier.ui.widgets.port_table import PortTable


class PortpierApp(App[None]):
    """portpier's TUI: live port dashboard over the psutil collector."""

    CSS = """
    Screen {
        background: $background;
    }
    """

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit", priority=True),
        Binding("ctrl+c", "quit", "Quit", priority=True, show=False),
        Binding("q", "quit", "Quit"),
        Binding("t", "cycle_theme", "Cycle theme"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.config = load()
        self.collector = Collector()
        for theme in THEMES.values():
            self.register_theme(theme)
        self.theme = self.config.theme if self.config.theme in THEMES else "dark"

    def get_default_screen(self) -> MainScreen:
        return MainScreen(
            self.collector,
            min_port=self.config.min_port,
            max_port=self.config.max_port,
            refresh_interval=self.config.refresh_interval,
        )

    def action_cycle_theme(self) -> None:
        index = THEME_NAMES.index(self.theme) if self.theme in THEME_NAMES else 0
        self.theme = THEME_NAMES[(index + 1) % len(THEME_NAMES)]
        # Widgets that bake theme colours into Rich Text must be told to re-render.
        self.query_one(StatusHeader).theme_name = self.theme
        self.query_one(PortTable).refresh_colors()
