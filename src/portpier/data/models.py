"""Immutable data models for the portpier data layer.

These dataclasses are deliberately free of any Textual or psutil dependency so
the data layer can be tested in isolation.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PortEntry:
    """A single network socket plus the metadata of the process that owns it.

    Any field sourced from the owning process may be ``None`` when psutil raised
    ``AccessDenied`` for that attribute — the entry is still produced.
    """

    port: int
    protocol: str  # "TCP" | "UDP"
    state: str  # "LISTEN" | "ESTABLISHED" | "TIME_WAIT" | "CLOSE_WAIT" | ...
    local_address: str  # "0.0.0.0" | "127.0.0.1" | "::" etc.
    remote_address: str | None  # None for LISTEN state
    pid: int | None
    process_name: str | None  # raw OS process name e.g. "node", "python3"
    process_type: str | None  # inferred label e.g. "Node.js", "Python"
    memory_rss_bytes: int | None  # Resident Set Size in bytes
    cpu_percent: float | None  # 0.0–100.0
    uptime_seconds: float | None  # seconds since process start
    user: str | None  # OS username owning the process
    status: str | None  # psutil process status string


@dataclass(frozen=True)
class DetailInfo:
    """Extended data fetched on demand when the user opens the detail panel."""

    entry: PortEntry
    cmdline: list[str]  # full argv e.g. ["node", "/app/server.js", "--port", "3000"]
    cwd: str | None  # working directory of the process
    parent_pid: int | None
    parent_name: str | None
    num_threads: int | None
    num_fds: int | None  # total open file descriptors
    fd_sample: list[str]  # first 20 readable fd paths/descriptions
    memory_vms_bytes: int | None  # Virtual Memory Size
    memory_percent: float | None  # % of total system RAM
    env_vars: dict[str, str]  # filtered env (see collector ENV filter)
    all_connections: list[PortEntry]  # all connections belonging to this PID
