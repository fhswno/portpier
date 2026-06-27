"""A centered modal listing every command-palette command.

Opened by the ``help`` command. Esc or q dismisses.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Label

# (command syntax, description). Kept in sync with ui/commands.py.
_COMMANDS: list[tuple[str, str]] = [
    ("toggle <column>", "Show or hide a column (e.g. toggle pid). PORT is always visible."),
    ("sort <column> [asc|desc]", "Sort by port, memory, cpu, or uptime."),
    ("theme <name>", "Switch theme: dark, light, paper, or matrix."),
    ("refresh <seconds>", "Set the refresh interval (0.5-60)."),
    (
        "port range <min> [max]",
        "Filter to a port range (e.g. port range 3000 9999). 'port range reset' clears it.",
    ),
    ("help", "Show this command reference."),
]


class HelpScreen(ModalScreen[None]):
    """A centered panel describing the available commands."""

    DEFAULT_CSS = """
    HelpScreen {
        align: center middle;
    }
    HelpScreen > #help-card {
        width: 78;
        max-width: 90%;
        height: auto;
        max-height: 80%;
        padding: 1 2;
        background: $surface;
        border: tall $primary;
    }
    HelpScreen #help-title {
        color: $primary;
        text-style: bold;
        width: 100%;
        content-align: center middle;
        padding-bottom: 1;
    }
    HelpScreen .help-cmd {
        color: $accent;
        text-style: bold;
    }
    HelpScreen .help-desc {
        color: $text-muted;
        padding-bottom: 1;
    }
    HelpScreen #help-footer {
        color: $text-muted;
        width: 100%;
        content-align: center middle;
        padding-top: 1;
    }
    """

    BINDINGS = [
        Binding("escape", "app.pop_screen", "Close", show=True),
        Binding("q", "app.pop_screen", "Close", show=False),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="help-card"):
            yield Label("portpier - Commands", id="help-title")
            for cmd, desc in _COMMANDS:
                cmd_label = Label(cmd, classes="help-cmd")
                yield cmd_label
                yield Label(desc, classes="help-desc")
            yield Label("[Esc] / [q] Close", id="help-footer")
