"""Entry point for the ``portpier`` CLI.

``--version`` / ``--help`` are handled by argparse and exit before the TUI is
imported; with no flags, the Textual dashboard is launched.
"""

from __future__ import annotations

import argparse

__version__ = "0.1.0"


def build_parser() -> argparse.ArgumentParser:
    """Construct the top-level argument parser for the ``portpier`` command."""
    parser = argparse.ArgumentParser(
        prog="portpier",
        description=(
            "A gorgeous, keyboard-driven TUI dashboard for monitoring and managing ports on macOS."
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
    # Imported lazily so `--version` / `--help` don't pay the Textual import cost.
    from portpier.app import PortpierApp

    PortpierApp().run()


if __name__ == "__main__":
    main()
