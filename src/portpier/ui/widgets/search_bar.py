"""Bottom search bar: a search input plus a live status on the right."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Input, Label


class SearchBar(Horizontal):
    """A single-line bar. The status shows the match count while filtering,
    and the command-palette hint otherwise."""

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
    SearchBar #search-status {
        width: auto;
        height: 1;
        padding: 0 1;
        color: $text-muted;
    }
    """

    def compose(self) -> ComposeResult:
        yield Input(placeholder="Search ports...", id="search-input")
        yield Label("[Ctrl+P] Commands", id="search-status")

    def set_status(self, query: str, matched: int, total: int) -> None:
        label = self.query_one("#search-status", Label)
        label.update(f"{matched} / {total} ports" if query else "[Ctrl+P] Commands")
