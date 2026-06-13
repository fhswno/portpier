"""Tests for data/collector.py.

psutil is mocked so these run deterministically on any machine. We patch
``process_iter`` (the per-process scan) and ``Process`` (used for cpu_percent
via the cache) on the collector's psutil reference.
"""

from __future__ import annotations

import socket
from collections.abc import Callable, Iterable
from types import SimpleNamespace
from typing import Any

import psutil
import pytest

from portpier.data import collector as collector_mod
from portpier.data.collector import Collector


def _addr(ip: str, port: int) -> SimpleNamespace:
    return SimpleNamespace(ip=ip, port=port)


def _conn(
    port: int,
    *,
    status: str = "LISTEN",
    proto: int = socket.SOCK_STREAM,
    ip: str = "0.0.0.0",
    raddr: tuple[str, int] | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        fd=3,
        family=socket.AF_INET,
        type=proto,
        laddr=_addr(ip, port),
        raddr=_addr(*raddr) if raddr is not None else (),
        status=status,
    )


def _full_info(pid: int = 1000, name: str = "node") -> dict[str, Any]:
    return {
        "pid": pid,
        "name": name,
        "username": "dave",
        "status": "running",
        "create_time": 0.0,
        "memory_info": SimpleNamespace(rss=1024, vms=2048),
        "num_threads": 4,
    }


class _FakeProc:
    def __init__(
        self,
        info: dict[str, Any],
        conns: list[SimpleNamespace] | None = None,
        conn_error: BaseException | None = None,
    ) -> None:
        self._info = info
        self._conns = conns or []
        self._conn_error = conn_error

    def net_connections(self, kind: str = "inet") -> list[SimpleNamespace]:
        if self._conn_error is not None:
            raise self._conn_error
        return self._conns

    def as_dict(self, attrs: list[str] | None = None, ad_value: Any = None) -> dict[str, Any]:
        return dict(self._info)


class _FakeCpuProc:
    def __init__(self, pid: int) -> None:
        self.pid = pid

    def cpu_percent(self, interval: float | None = None) -> float:
        return 3.5


@pytest.fixture
def patch_psutil(
    monkeypatch: pytest.MonkeyPatch,
) -> Callable[[Iterable[_FakeProc]], None]:
    def _apply(procs: Iterable[_FakeProc]) -> None:
        proc_list = list(procs)
        monkeypatch.setattr(
            collector_mod.psutil, "process_iter", lambda *a, **k: iter(proc_list)
        )
        monkeypatch.setattr(collector_mod.psutil, "Process", _FakeCpuProc)

    return _apply


def test_returns_only_ports_at_or_above_min(
    patch_psutil: Callable[[Iterable[_FakeProc]], None],
) -> None:
    proc = _FakeProc(_full_info(), conns=[_conn(80), _conn(1024), _conn(3000), _conn(70000)])
    patch_psutil([proc])
    entries = Collector().collect_ports()
    assert {e.port for e in entries} == {1024, 3000}  # 80 below floor, 70000 above max


def test_custom_min_port_filters_below(
    patch_psutil: Callable[[Iterable[_FakeProc]], None],
) -> None:
    proc = _FakeProc(_full_info(), conns=[_conn(1024), _conn(3000), _conn(9000)])
    patch_psutil([proc])
    entries = Collector().collect_ports(min_port=3000)
    assert all(e.port >= 3000 for e in entries)
    assert {e.port for e in entries} == {3000, 9000}


def test_system_port_floor_is_enforced_even_below_1024(
    patch_psutil: Callable[[Iterable[_FakeProc]], None],
) -> None:
    proc = _FakeProc(_full_info(), conns=[_conn(80), _conn(8080)])
    patch_psutil([proc])
    entries = Collector().collect_ports(min_port=80)
    assert {e.port for e in entries} == {8080}


def test_no_such_process_is_skipped_gracefully(
    patch_psutil: Callable[[Iterable[_FakeProc]], None],
) -> None:
    good = _FakeProc(_full_info(pid=1, name="node"), conns=[_conn(3000)])
    dead = _FakeProc(_full_info(pid=2), conn_error=psutil.NoSuchProcess(2))
    patch_psutil([dead, good])
    entries = Collector().collect_ports()
    assert {e.port for e in entries} == {3000}  # no crash; dead process dropped


def test_access_denied_yields_none_metadata_not_a_crash(
    patch_psutil: Callable[[Iterable[_FakeProc]], None],
) -> None:
    # as_dict(ad_value=None) returns None per denied attribute; connections still come back
    denied_info: dict[str, Any] = {
        "pid": 5,
        "name": None,
        "username": None,
        "status": None,
        "create_time": None,
        "memory_info": None,
        "num_threads": None,
    }
    proc = _FakeProc(denied_info, conns=[_conn(4000)])
    patch_psutil([proc])
    entries = Collector().collect_ports()
    assert len(entries) == 1
    entry = entries[0]
    assert entry.port == 4000
    assert entry.process_name is None
    assert entry.process_type is None
    assert entry.memory_rss_bytes is None
    assert entry.uptime_seconds is None
    assert entry.user is None
    assert entry.status is None


def test_identical_sockets_are_deduplicated(
    patch_psutil: Callable[[Iterable[_FakeProc]], None],
) -> None:
    proc = _FakeProc(_full_info(), conns=[_conn(8080), _conn(8080)])
    patch_psutil([proc])
    assert len(Collector().collect_ports()) == 1


def test_dedup_key_keeps_distinct_remote_addresses(
    patch_psutil: Callable[[Iterable[_FakeProc]], None],
) -> None:
    proc = _FakeProc(
        _full_info(),
        conns=[
            _conn(8080, status="ESTABLISHED", raddr=("1.1.1.1", 50000)),
            _conn(8080, status="ESTABLISHED", raddr=("2.2.2.2", 50000)),
        ],
    )
    patch_psutil([proc])
    assert len(Collector().collect_ports()) == 2


def test_metadata_is_populated_for_owned_process(
    patch_psutil: Callable[[Iterable[_FakeProc]], None],
) -> None:
    proc = _FakeProc(_full_info(pid=4321, name="node"), conns=[_conn(3000)])
    patch_psutil([proc])
    entry = Collector().collect_ports()[0]
    assert entry.pid == 4321
    assert entry.process_name == "node"
    assert entry.process_type == "Node.js"
    assert entry.memory_rss_bytes == 1024
    assert entry.cpu_percent == 3.5
    assert entry.user == "dave"
