"""Configuration: dataclass, validated load, and atomic save.

The config lives at ``~/.config/portpier/config.toml``. It is read with the
stdlib ``tomllib`` and written with ``tomli_w``. The file is created only when a
setting is changed (the UI calls :func:`save`), never on a plain load.
"""

from __future__ import annotations

import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import tomli_w

SCHEMA_VERSION = 1
MIN_PORT_FLOOR = 1024  # invariant: system ports (< 1024) are never shown
MIN_REFRESH = 0.5
MAX_REFRESH = 60.0
DEFAULT_COLUMNS = ["port", "process", "type", "pid", "memory", "cpu", "state", "uptime"]

CONFIG_DIR = Path.home() / ".config" / "portpier"
CONFIG_PATH = CONFIG_DIR / "config.toml"


@dataclass
class Config:
    """Runtime configuration with sensible zero-config defaults."""

    schema_version: int = SCHEMA_VERSION

    # Display
    theme: str = "dark"  # "dark" | "light" | "paper" | "matrix"
    refresh_interval: float = 2.0  # seconds; clamped to [0.5, 60.0]
    columns: list[str] = field(default_factory=lambda: list(DEFAULT_COLUMNS))
    default_sort_column: str = "port"  # "port" | "process" | "memory" | "cpu" | "uptime"
    default_sort_order: str = "asc"  # "asc" | "desc"

    # Filters
    min_port: int = MIN_PORT_FLOOR  # hard floor: never < 1024
    max_port: int = 65535


def _warn(message: str) -> None:
    print(f"portpier: {message}", file=sys.stderr)


def _get_str(data: dict[str, Any], key: str, default: str) -> str:
    value = data.get(key, default)
    return value if isinstance(value, str) else default


def _get_int(data: dict[str, Any], key: str, default: int) -> int:
    value = data.get(key, default)
    if isinstance(value, bool):  # bool is a subclass of int — reject it
        return default
    return value if isinstance(value, int) else default


def _get_float(data: dict[str, Any], key: str, default: float) -> float:
    value = data.get(key, default)
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    return default


def _get_str_list(data: dict[str, Any], key: str, default: list[str]) -> list[str]:
    value = data.get(key, default)
    if isinstance(value, list):
        strings = [item for item in value if isinstance(item, str)]
        if len(strings) == len(value):
            return strings
    return list(default)


def _clamp_refresh(value: float) -> float:
    return max(MIN_REFRESH, min(value, MAX_REFRESH))


def load(path: Path | None = None) -> Config:
    """Load and validate the config, falling back to defaults on any problem.

    - Missing file → defaults (the file is not created).
    - Unparseable file → warn to stderr, defaults.
    - Missing/unknown ``schema_version`` → warn to stderr, defaults.
    - ``min_port`` below 1024 → clamped silently. ``refresh_interval`` is
      clamped to [0.5, 60.0]. Unknown keys are ignored.
    """
    target = path if path is not None else CONFIG_PATH
    if not target.exists():
        return Config()

    try:
        with target.open("rb") as handle:
            data = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        _warn(f"could not read config {target}: {exc}; using defaults")
        return Config()

    version = data.get("schema_version")
    if version != SCHEMA_VERSION:
        _warn(f"unknown or missing config schema_version ({version!r}); using defaults")
        return Config()

    display = data.get("display", {})
    filters = data.get("filters", {})
    if not isinstance(display, dict):
        display = {}
    if not isinstance(filters, dict):
        filters = {}

    defaults = Config()
    return Config(
        schema_version=SCHEMA_VERSION,
        theme=_get_str(display, "theme", defaults.theme),
        refresh_interval=_clamp_refresh(
            _get_float(display, "refresh_interval", defaults.refresh_interval)
        ),
        columns=_get_str_list(display, "columns", DEFAULT_COLUMNS),
        default_sort_column=_get_str(display, "default_sort_column", defaults.default_sort_column),
        default_sort_order=_get_str(display, "default_sort_order", defaults.default_sort_order),
        min_port=max(_get_int(filters, "min_port", defaults.min_port), MIN_PORT_FLOOR),
        max_port=_get_int(filters, "max_port", defaults.max_port),
    )


def save(config: Config, path: Path | None = None) -> None:
    """Persist ``config`` atomically (write to a temp file, then ``os.replace``).

    Creates the parent directory if absent. Re-saving an unchanged config
    produces a byte-identical file.
    """
    target = path if path is not None else CONFIG_PATH
    target.parent.mkdir(parents=True, exist_ok=True)

    document: dict[str, Any] = {
        "schema_version": config.schema_version,
        "display": {
            "theme": config.theme,
            "refresh_interval": config.refresh_interval,
            "columns": config.columns,
            "default_sort_column": config.default_sort_column,
            "default_sort_order": config.default_sort_order,
        },
        "filters": {
            "min_port": config.min_port,
            "max_port": config.max_port,
        },
    }

    tmp = target.with_name(target.name + ".tmp")
    with tmp.open("wb") as handle:
        tomli_w.dump(document, handle)
    tmp.replace(target)
