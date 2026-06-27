"""psutil-backed collection of ports and process detail.

The collector is a *class* (not free functions) so it can hold ``_process_cache``
across refresh cycles without a module-level global. ``PortpierApp``
owns a single instance.

macOS strategy: iterate processes and ask each one for its connections, rather
than calling the system-wide ``psutil.net_connections()`` — the latter does not
reliably return PIDs without root on macOS.
"""

from __future__ import annotations

import socket
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar

import psutil

from portpier.data.models import DetailInfo, PortEntry
from portpier.utils.inference import infer_process_type

_T = TypeVar("_T")

_MIN_PORT_FLOOR = 1024  # invariant: system ports are never shown
_UNKNOWN_PROTO = "?"
_PROC_ATTRS = ["pid", "name", "username", "status", "create_time", "memory_info", "num_threads"]

_PROTO_BY_TYPE: dict[int, str] = {
    int(socket.SOCK_STREAM): "TCP",
    int(socket.SOCK_DGRAM): "UDP",
}

# Only these environment keys are ever surfaced in the detail panel (security + noise).
_ENV_KEYS = frozenset(
    {
        "PORT",
        "NODE_ENV",
        "PYTHON_ENV",
        "APP_ENV",
        "DEBUG",
        "HOST",
        "RAILS_ENV",
        "RACK_ENV",
        "DJANGO_SETTINGS_MODULE",
        "FLASK_ENV",
        "DATABASE_URL",
        "REDIS_URL",
    }
)


def _safe(getter: Callable[[], _T]) -> _T | None:
    """Run a psutil getter, returning ``None`` on any psutil error."""
    try:
        return getter()
    except psutil.Error:
        return None


@dataclass(frozen=True)
class _ProcMeta:
    """Per-process metadata, fetched once per PID per cycle."""

    pid: int | None
    name: str | None
    process_type: str | None
    memory_rss_bytes: int | None
    cpu_percent: float | None
    uptime_seconds: float | None
    user: str | None
    status: str | None


def _empty_detail(entry: PortEntry) -> DetailInfo:
    """A DetailInfo with everything blank — used when the process is gone."""
    return DetailInfo(
        entry=entry,
        cmdline=[],
        cwd=None,
        parent_pid=None,
        parent_name=None,
        num_threads=None,
        num_fds=None,
        fd_sample=[],
        memory_vms_bytes=None,
        memory_percent=None,
        env_vars={},
        all_connections=[],
    )


class Collector:
    """Owns all psutil interaction. Instantiated once by ``PortpierApp``."""

    def __init__(self) -> None:
        # Persisted across cycles so cpu_percent() can diff against a prior
        # sample. Without this, every cycle is a "first call" and reads 0.0.
        self._process_cache: dict[int, psutil.Process] = {}
        # Set on each scan: True if any process raised AccessDenied this cycle
        # (i.e. other users' processes exist that we can't inspect without sudo).
        # Read by the UI to toggle the "sudo required" header warning.
        self.access_denied: bool = False

    # -- public API ----------------------------------------------------------

    def collect_ports(self, min_port: int = 1024, max_port: int = 65535) -> list[PortEntry]:
        """Return all in-range connections, one ``PortEntry`` per logical socket.

        Per-process iteration; ``AccessDenied``/``NoSuchProcess`` on a process is
        caught and that process is skipped (its connections do not appear).
        Metadata fields denied per-attribute come back as ``None``. Sorting is
        left to the UI layer.
        """
        floor = max(min_port, _MIN_PORT_FLOOR)
        now = time.time()
        entries: list[PortEntry] = []
        seen: set[tuple[str, str, int, str, str]] = set()
        live_pids: set[int] = set()
        any_denied = False

        for proc in psutil.process_iter():
            try:
                connections = proc.net_connections(kind="inet")
                info = proc.as_dict(attrs=_PROC_ATTRS, ad_value=None)
            except psutil.NoSuchProcess:
                continue
            except psutil.AccessDenied:
                # Process owned by another user — we can't see its sockets.
                # Surface this so the UI can show the "sudo required" warning.
                any_denied = True
                continue
            except psutil.Error:
                continue
            if not connections:
                continue

            meta = self._meta_from_info(info, now)
            for conn in connections:
                laddr = conn.laddr
                if not laddr:
                    continue
                port = laddr.port
                if port < floor or port > max_port:
                    continue
                protocol = _PROTO_BY_TYPE.get(int(conn.type), _UNKNOWN_PROTO)
                raddr = conn.raddr
                remote = f"{raddr.ip}:{raddr.port}" if raddr else None
                key = (protocol, laddr.ip, port, remote or "", conn.status)
                if key in seen:
                    continue
                seen.add(key)
                entries.append(
                    PortEntry(
                        port=port,
                        protocol=protocol,
                        state=conn.status,
                        local_address=laddr.ip,
                        remote_address=remote,
                        pid=meta.pid,
                        process_name=meta.name,
                        process_type=meta.process_type,
                        memory_rss_bytes=meta.memory_rss_bytes,
                        cpu_percent=meta.cpu_percent,
                        uptime_seconds=meta.uptime_seconds,
                        user=meta.user,
                        status=meta.status,
                    )
                )
                if meta.pid is not None:
                    live_pids.add(meta.pid)

        self._evict_stale(live_pids)
        self.access_denied = any_denied
        return entries

    def collect_detail(self, pid: int, entry: PortEntry) -> DetailInfo:
        """Fetch extended info for ``pid`` on demand (detail panel only).

        Reuses ``_process_cache`` where possible. Individual fields denied by
        the OS come back as ``None``/empty — never raises. On macOS,
        ``open_files()`` and ``environ()`` are frequently restricted even for
        your own processes, so ``fd_sample`` / ``env_vars`` are often empty.
        """
        proc = self._process_cache.get(pid)
        if proc is None:
            try:
                proc = psutil.Process(pid)
            except psutil.Error:
                return _empty_detail(entry)
            self._process_cache[pid] = proc

        memory_info = _safe(proc.memory_info)
        parent_pid = _safe(proc.ppid)
        parent_name: str | None = None
        if parent_pid is not None:
            parent = _safe(lambda: psutil.Process(parent_pid))
            if parent is not None:
                parent_name = _safe(parent.name)

        fd_sample: list[str] = []
        open_files = _safe(proc.open_files)
        if open_files:
            fd_sample = [f.path for f in open_files[:20]]

        env_vars: dict[str, str] = {}
        environ = _safe(proc.environ)
        if environ:
            env_vars = {k: v for k, v in environ.items() if k in _ENV_KEYS}

        return DetailInfo(
            entry=entry,
            cmdline=_safe(proc.cmdline) or [],
            cwd=_safe(proc.cwd),
            parent_pid=parent_pid,
            parent_name=parent_name,
            num_threads=_safe(proc.num_threads),
            num_fds=_safe(proc.num_fds),
            fd_sample=fd_sample,
            memory_vms_bytes=memory_info.vms if memory_info is not None else None,
            memory_percent=_safe(proc.memory_percent),
            env_vars=env_vars,
            all_connections=self._all_connections(proc, entry),
        )

    # -- internals -----------------------------------------------------------

    def _meta_from_info(self, info: dict[str, Any], now: float) -> _ProcMeta:
        raw_pid = info.get("pid")
        pid = raw_pid if isinstance(raw_pid, int) and not isinstance(raw_pid, bool) else None
        name = info.get("name")
        memory_info = info.get("memory_info")
        create_time = info.get("create_time")
        return _ProcMeta(
            pid=pid,
            name=name if isinstance(name, str) else None,
            process_type=infer_process_type(name if isinstance(name, str) else None),
            memory_rss_bytes=memory_info.rss if memory_info is not None else None,
            cpu_percent=self._cpu_percent(pid) if pid is not None else None,
            uptime_seconds=(now - create_time) if create_time is not None else None,
            user=info.get("username") if isinstance(info.get("username"), str) else None,
            status=info.get("status") if isinstance(info.get("status"), str) else None,
        )

    def _cpu_percent(self, pid: int) -> float | None:
        """CPU% via a cached Process object so the delta is meaningful."""
        proc = self._process_cache.get(pid)
        if proc is None:
            try:
                proc = psutil.Process(pid)
            except psutil.Error:
                return None
            self._process_cache[pid] = proc
        try:
            return proc.cpu_percent(interval=None)
        except psutil.Error:
            self._process_cache.pop(pid, None)
            return None

    def _all_connections(self, proc: psutil.Process, entry: PortEntry) -> list[PortEntry]:
        connections = _safe(lambda: proc.net_connections(kind="inet"))
        if not connections:
            return []
        result: list[PortEntry] = []
        for conn in connections:
            laddr = conn.laddr
            if not laddr:
                continue
            raddr = conn.raddr
            result.append(
                PortEntry(
                    port=laddr.port,
                    protocol=_PROTO_BY_TYPE.get(int(conn.type), _UNKNOWN_PROTO),
                    state=conn.status,
                    local_address=laddr.ip,
                    remote_address=f"{raddr.ip}:{raddr.port}" if raddr else None,
                    pid=entry.pid,
                    process_name=entry.process_name,
                    process_type=entry.process_type,
                    memory_rss_bytes=entry.memory_rss_bytes,
                    cpu_percent=entry.cpu_percent,
                    uptime_seconds=entry.uptime_seconds,
                    user=entry.user,
                    status=entry.status,
                )
            )
        return result

    def _evict_stale(self, live_pids: set[int]) -> None:
        for pid in list(self._process_cache):
            if pid not in live_pids:
                del self._process_cache[pid]
