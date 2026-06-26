"""The top status bar: app name, port count, total memory, theme, refresh rate."""

from __future__ import annotations

from rich.text import Text
from textual.app import RenderResult
from textual.reactive import reactive
from textual.widget import Widget

from portpier.ui.themes import TOKENS

_SEP = "  ·  "


class StatusHeader(Widget):
    """Single-line header. Values are reactive so live data can update them."""

    DEFAULT_CSS = """
    StatusHeader {
        height: 1;
        width: 1fr;
        background: $header-bg;
        color: $foreground;
        padding: 0 1;
    }
    """

    port_count: reactive[int] = reactive(0)
    total_memory: reactive[str] = reactive("0 B")
    theme_name: reactive[str] = reactive("dark")
    refresh_interval: reactive[float] = reactive(2.0)
    pulsing: reactive[bool] = reactive(False)
    sudo_warning: reactive[bool] = reactive(False)

    def render(self) -> RenderResult:
        tokens = TOKENS.get(self.theme_name, TOKENS["dark"])
        line = Text(no_wrap=True, overflow="ellipsis")
        line.append("portpier", style=f"bold {tokens['accent']}")
        line.append(_SEP)
        line.append(f"{self.port_count} ports")
        line.append(_SEP)
        line.append(f"{self.total_memory} total")
        line.append(_SEP)
        line.append(f"theme: {self.theme_name}")
        line.append(_SEP)
        line.append("↻", style="reverse" if self.pulsing else "")
        line.append(f" {self._format_interval()}")
        if self.sudo_warning:
            line.append(_SEP)
            line.append("⚠ Some processes require sudo to inspect", style=tokens["danger"])
        return line

    def pulse(self) -> None:
        """Briefly invert the ↻ glyph to signal a successful data refresh."""
        self.pulsing = True
        self.set_timer(0.25, self._end_pulse)

    def _end_pulse(self) -> None:
        self.pulsing = False

    def _format_interval(self) -> str:
        value = self.refresh_interval
        return f"{int(value)}s" if value == int(value) else f"{value}s"
