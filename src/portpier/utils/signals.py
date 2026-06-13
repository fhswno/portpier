"""Process signalling. The single entry point never raises."""

from __future__ import annotations

import os
import signal


def send_signal(pid: int, sig: signal.Signals) -> tuple[bool, str]:
    """Send ``sig`` to ``pid``.

    Returns ``(success, message)``. Handles ProcessLookupError (already gone),
    PermissionError (EPERM), and any other OSError. Never raises.
    """
    try:
        os.kill(pid, sig)
    except ProcessLookupError:
        return (False, f"Process {pid} no longer exists")
    except PermissionError:
        return (False, "Permission denied — try running portpier with sudo")
    except OSError as exc:
        return (False, f"Failed to signal process {pid}: {exc}")
    return (True, f"Sent {sig.name} to PID {pid}")
