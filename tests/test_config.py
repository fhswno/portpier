"""Tests for config.py."""

from __future__ import annotations

import tomllib
from pathlib import Path

from portpier.config import DEFAULT_COLUMNS, Config, load, save


def test_default_values() -> None:
    cfg = Config()
    assert cfg.schema_version == 1
    assert cfg.theme == "dark"
    assert cfg.refresh_interval == 2.0
    assert cfg.default_sort_column == "port"
    assert cfg.default_sort_order == "asc"
    assert cfg.min_port == 1024
    assert cfg.max_port == 65535
    assert cfg.columns == DEFAULT_COLUMNS


def test_load_missing_file_returns_defaults_without_creating_it(tmp_path: Path) -> None:
    target = tmp_path / "config.toml"
    cfg = load(target)
    assert cfg == Config()
    assert not target.exists()


def test_load_valid_toml(tmp_path: Path) -> None:
    target = tmp_path / "config.toml"
    target.write_text(
        "schema_version = 1\n"
        "[display]\n"
        'theme = "matrix"\n'
        "refresh_interval = 5.0\n"
        "[filters]\n"
        "min_port = 3000\n"
        "max_port = 4000\n"
    )
    cfg = load(target)
    assert cfg.theme == "matrix"
    assert cfg.refresh_interval == 5.0
    assert cfg.min_port == 3000
    assert cfg.max_port == 4000


def test_load_missing_keys_use_defaults(tmp_path: Path) -> None:
    target = tmp_path / "config.toml"
    target.write_text('schema_version = 1\n[display]\ntheme = "light"\n')
    cfg = load(target)
    assert cfg.theme == "light"
    assert cfg.refresh_interval == 2.0  # default
    assert cfg.min_port == 1024  # default


def test_load_unknown_keys_are_ignored(tmp_path: Path) -> None:
    target = tmp_path / "config.toml"
    target.write_text('schema_version = 1\n[display]\nbogus = "x"\ntheme = "paper"\n')
    cfg = load(target)
    assert cfg.theme == "paper"


def test_min_port_is_clamped_to_floor(tmp_path: Path) -> None:
    target = tmp_path / "config.toml"
    target.write_text("schema_version = 1\n[filters]\nmin_port = 80\n")
    cfg = load(target)
    assert cfg.min_port == 1024


def test_unknown_schema_version_falls_back_to_defaults(tmp_path: Path) -> None:
    target = tmp_path / "config.toml"
    target.write_text('schema_version = 999\n[display]\ntheme = "light"\n')
    assert load(target) == Config()


def test_refresh_interval_is_clamped(tmp_path: Path) -> None:
    target = tmp_path / "config.toml"
    target.write_text("schema_version = 1\n[display]\nrefresh_interval = 0.1\n")
    assert load(target).refresh_interval == 0.5


def test_save_creates_file_and_parent_dir(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "config.toml"
    save(Config(theme="matrix"), target)
    assert target.exists()
    data = tomllib.loads(target.read_text())
    assert data["display"]["theme"] == "matrix"
    assert data["filters"]["min_port"] == 1024


def test_save_is_idempotent(tmp_path: Path) -> None:
    target = tmp_path / "config.toml"
    cfg = Config(theme="light")
    save(cfg, target)
    first = target.read_bytes()
    save(cfg, target)
    assert target.read_bytes() == first


def test_round_trip(tmp_path: Path) -> None:
    target = tmp_path / "config.toml"
    original = Config(theme="paper", refresh_interval=3.0, min_port=2000, max_port=9000)
    save(original, target)
    assert load(target) == original
