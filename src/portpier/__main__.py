"""Entry point for the portpier CLI.

Phase 0 skeleton: argument parsing only. The TUI is wired up in a later phase.
"""

from __future__ import annotations

import argparse

__version__ = "0.1.0"


def build_parser() -> argparse.ArgumentParser:
    """Construct the top-level argument parser for the ``portpier`` command."""
    parser = argparse.ArgumentParser(
        prog="portpier",
        description=(
            "A gorgeous, keyboard-driven TUI dashboard for monitoring and "
            "managing ports on macOS."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"portpier {__version__}",
    )
    return parser


def main() -> None:
    """CLI entry point. ``--version`` and ``--help`` exit during parsing."""
    parser = build_parser()
    parser.parse_args()
    # Phase 0: nothing runs yet. A bare `portpier` invocation will launch the
    # TUI once the application is implemented (Phase 2).
    print("portpier: TUI not yet implemented (Phase 0 skeleton).")


if __name__ == "__main__":
    main()
