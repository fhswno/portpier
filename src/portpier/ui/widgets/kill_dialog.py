"""The kill-confirmation modal.

Opened with ``k`` from the main table or the detail screen. It captures only
plain values (pid, port, process name) — never a PortEntry or row index — so the
signal always targets the originally selected process even as the table refreshes
behind it (see CLAUDE.md §8.6).

The dialog does the kill itself: it calls :func:`send_signal`, shows the
appropriate toast, and dismisses with ``True`` on success / ``False`` otherwise.
A ``cancel`` (Esc or the Cancel button) dismisses with ``False`` and does nothing.
"""

from __future__ import annotations

import signal

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.notifications import SeverityLevel
from textual.screen import ModalScreen
from textual.widgets import Button, Static

from portpier.utils.signals import send_signal


class KillConfirmDialog(ModalScreen[bool]):
    """Modal that asks the user how to terminate a process, then does it."""

    DEFAULT_CSS = """
    KillConfirmDialog {
        align: center middle;
    }
    #kill-card {
        width: 64;
        height: auto;
        padding: 1 2;
        background: $surface;
        border: tall $primary;
    }
    #kill-title {
        color: $primary;
        text-style: bold;
        padding-bottom: 1;
    }
    #kill-target {
        padding-bottom: 1;
    }
    #kill-prompt {
        color: $text-muted;
        padding-bottom: 1;
    }
    #kill-actions {
        height: auto;
        align-horizontal: center;
        padding-bottom: 1;
    }
    #kill-actions Button {
        margin: 0 1;
    }
    #cancel {
        width: 100%;
    }

    /* Strong, obvious interaction states so mouse hover and keyboard focus
       are both unmistakable — and so arrow-key nav between buttons reads. */
    KillConfirmDialog Button:hover {
        background: $boost;
        border: tall $accent;
        text-style: bold;
    }
    KillConfirmDialog #force:hover {
        border: tall $error;
    }
    KillConfirmDialog #graceful:focus,
    KillConfirmDialog #cancel:focus {
        background: $accent;
        color: $background;
        text-style: bold;
        border: tall $accent;
    }
    /* Force Kill keeps its red identity even when focused. */
    KillConfirmDialog #force:focus {
        background: $error;
        color: $background;
        text-style: bold;
        border: tall $error;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=True),
        # Arrow keys hop between buttons (alongside Tab/Shift+Tab), so reaching
        # Force Kill from Graceful is a single, obvious keypress.
        Binding("right", "next_button", show=False),
        Binding("down", "next_button", show=False),
        Binding("left", "prev_button", show=False),
        Binding("up", "prev_button", show=False),
    ]

    def __init__(self, pid: int, port: int, process_name: str) -> None:
        super().__init__()
        self._pid = pid
        self._port = port
        self._name = process_name

    def compose(self) -> ComposeResult:
        with Vertical(id="kill-card"):
            yield Static("Kill Process", id="kill-title")
            yield Static(
                f"{self._name}  (PID {self._pid})  ·  port {self._port}",
                id="kill-target",
            )
            yield Static("Choose termination method:", id="kill-prompt")
            with Horizontal(id="kill-actions"):
                yield Button("Graceful (SIGTERM)", id="graceful")
                yield Button("Force Kill (SIGKILL)", id="force", variant="error")
            yield Button("Cancel", id="cancel")

    def on_mount(self) -> None:
        # Default focus: Graceful — Enter immediately sends SIGTERM.
        self.query_one("#graceful", Button).focus()

    # -- interactions --------------------------------------------------------

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "graceful":
            self._do_kill(signal.SIGTERM)
        elif button_id == "force":
            self._do_kill(signal.SIGKILL)
        elif button_id == "cancel":
            self.dismiss(False)

    def action_cancel(self) -> None:
        self.dismiss(False)

    def action_next_button(self) -> None:
        self.app.action_focus_next()

    def action_prev_button(self) -> None:
        self.app.action_focus_previous()

    # -- the actual signal ---------------------------------------------------

    def _do_kill(self, sig: signal.Signals) -> None:
        success, message = send_signal(self._pid, sig)
        if success:
            self.app.notify(
                f"Sent {sig.name} to {self._name} (PID {self._pid})",
                severity="information",
            )
            self.dismiss(True)
        else:
            self.app.notify(message, severity=self._failure_severity(message))
            self.dismiss(False)

    @staticmethod
    def _failure_severity(message: str) -> SeverityLevel:
        # send_signal's messages are internal and stable; classify for the toast.
        if "no longer exists" in message:
            return "warning"
        return "error"
