"""Bottom search bar. Renders only — filtering is wired up in a later phase."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Input, Label


class SearchBar(Horizontal):
    """A single-line bar: a search input on the left, a command hint on the right."""

    DEFAULT_CSS = """
    SearchBar {
        dock: bottom;
        height: 1;
        width: 1fr;
        background: $panel;
    }
    SearchBar Input {
        border: none;
        height: 1;
        min-height: 1;
        padding: 0 1;
        width: 1fr;
        background: $panel;
        color: $foreground;
    }
    SearchBar Input:focus {
        /* Textual re-adds a border on focus; keep it off so the 1-row input
           doesn't collapse (the border would eat the only line). */
        border: none;
        background: $surface;
    }
    SearchBar #commands-hint {
        width: auto;
        height: 1;
        padding: 0 1;
        color: $text-muted;
    }
    """

    def compose(self) -> ComposeResult:
        yield Input(placeholder="Search ports...", id="search-input")
        yield Label("[Ctrl+P] Commands", id="commands-hint")
