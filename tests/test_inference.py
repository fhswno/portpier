"""Tests for utils/inference.py (CLAUDE.md §15)."""

from __future__ import annotations

from portpier.utils.inference import PROCESS_TYPE_MAP, infer_process_type


def test_every_key_maps_to_its_label() -> None:
    for name, label in PROCESS_TYPE_MAP.items():
        assert infer_process_type(name) == label


def test_unknown_name_returns_none() -> None:
    assert infer_process_type("totally-unknown-binary") is None


def test_matching_is_case_insensitive() -> None:
    assert infer_process_type("NODE") == "Node.js"
    assert infer_process_type("Python3") == "Python"


def test_none_input_returns_none() -> None:
    assert infer_process_type(None) is None


def test_basename_is_used() -> None:
    assert infer_process_type("/usr/local/bin/node") == "Node.js"
