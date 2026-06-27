"""The root Textual application."""

from __future__ import annotations

from textual.app import App
from textual.binding import Binding

from portpier.config import (
    CONFIG_PATH,
    DEFAULT_COLUMNS,
    MAX_REFRESH,
    MIN_PORT_FLOOR,
    MIN_REFRESH,
    load,
    save,
)
from portpier.data.collector import Collector
from portpier.ui.commands import PortpierCommandProvider
from portpier.ui.screens.main import MainScreen
from portpier.ui.themes import THEME_NAMES, THEMES
from portpier.ui.widgets.header import StatusHeader
from portpier.ui.widgets.help_dialog import HelpScreen
from portpier.ui.widgets.port_table import COLUMN_KEYS, SORTABLE, PortTable


class PortpierApp(App[None]):
    """portpier's TUI: live port dashboard over the psutil collector."""

    CSS = """
    Screen {
        background: $background;
    }
    """

    # Keep Textual's built-in commands (Quit, etc.) and add our own.
    COMMANDS = App.COMMANDS | {PortpierCommandProvider}

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
        # Direct handle on the main screen so command callbacks can reach it
        # without depending on which screen happens to be active (e.g. while a
        # modal is open).
        self.main_screen: MainScreen | None = None
        for theme in THEMES.values():
            self.register_theme(theme)
        self.theme = self.config.theme if self.config.theme in THEMES else "dark"

    def get_default_screen(self) -> MainScreen:
        screen = MainScreen(
            self.collector,
            min_port=self.config.min_port,
            max_port=self.config.max_port,
            refresh_interval=self.config.refresh_interval,
            sort_column=self.config.default_sort_column,
            sort_order=self.config.default_sort_order,
            columns=list(self.config.columns),
        )
        self.main_screen = screen
        return screen

    # -- persistence ---------------------------------------------------------

    def _persist(self) -> None:
        """Atomic-write the current config, toasting on failure (never raise)."""
        try:
            save(self.config)
        except OSError as exc:
            self.notify(
                f"Config could not be saved: {CONFIG_PATH} not writable ({exc})",
                severity="error",
            )

    # -- command-palette dispatch -------------------------------------------

    def set_theme(self, name: str) -> None:
        if name not in THEMES:
            return
        self.config.theme = name
        self.theme = name
        self._persist()
        screen = self.main_screen
        if screen is not None:
            screen.query_one(StatusHeader).theme_name = name
            screen.query_one(PortTable).refresh_colors()

    def apply_sort(self, column: str, descending: bool) -> None:
        if column not in SORTABLE:
            return
        self.config.default_sort_column = column
        self.config.default_sort_order = "desc" if descending else "asc"
        self._persist()
        if self.main_screen is not None:
            self.main_screen.set_sort(column, descending)

    def apply_refresh_interval(self, seconds: float) -> None:
        clamped = max(MIN_REFRESH, min(seconds, MAX_REFRESH))
        self.config.refresh_interval = clamped
        self._persist()
        if self.main_screen is not None:
            self.main_screen.set_refresh_interval(clamped)

    def apply_port_range(self, min_port: int, max_port: int) -> None:
        lo = max(min_port, MIN_PORT_FLOOR)
        hi = max(max_port, lo)
        self.config.min_port = lo
        self.config.max_port = hi
        self._persist()
        if self.main_screen is not None:
            self.main_screen.set_port_range(lo, hi)

    def apply_column_toggle(self, column: str) -> None:
        if column == "port":
            self.notify("PORT column is always visible")
            return
        if column not in COLUMN_KEYS:
            return
        new_set = set(self.config.columns) ^ {column}
        self.config.columns = [c for c in DEFAULT_COLUMNS if c in new_set]
        self._persist()
        if self.main_screen is not None:
            self.main_screen.set_column_visibility(self.config.columns)

    def open_help(self) -> None:
        self.push_screen(HelpScreen())

    # -- keybindings ---------------------------------------------------------

    def action_cycle_theme(self) -> None:
        index = THEME_NAMES.index(self.theme) if self.theme in THEME_NAMES else 0
        self.set_theme(THEME_NAMES[(index + 1) % len(THEME_NAMES)])
