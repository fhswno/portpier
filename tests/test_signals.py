"""Tests for utils/signals.py.

``os.kill`` is monkeypatched so these run deterministically and without
actually signalling anything.
"""

from __future__ import annotations

import os
import signal

import pytest

from portpier.utils.signals import send_signal


def test_send_signal_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(os, "kill", lambda pid, sig: None)
    ok, message = send_signal(123, signal.SIGTERM)
    assert ok is True
    assert "SIGTERM" in message
    assert "123" in message


def test_send_signal_force_kill_label(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(os, "kill", lambda pid, sig: None)
    ok, message = send_signal(456, signal.SIGKILL)
    assert ok is True
    assert "SIGKILL" in message


def test_send_signal_process_gone(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_gone(pid: int, sig: int) -> None:
        raise ProcessLookupError()

    monkeypatch.setattr(os, "kill", raise_gone)
    ok, message = send_signal(123, signal.SIGTERM)
    assert ok is False
    assert "no longer exists" in message
    assert "123" in message


def test_send_signal_permission_denied(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_perm(pid: int, sig: int) -> None:
        raise PermissionError()

    monkeypatch.setattr(os, "kill", raise_perm)
    ok, message = send_signal(123, signal.SIGTERM)
    assert ok is False
    assert "Permission denied" in message
