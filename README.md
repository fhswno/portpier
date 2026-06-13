# portpier

> A gorgeous, keyboard-driven TUI dashboard for monitoring and managing ports on macOS.
> Built with Python + Textual + psutil.

> [!NOTE]
> **Early development.** The data layer and UI are being built phase by phase
> (see [`CLAUDE.md`](./CLAUDE.md)). Right now the `portpier` command is a working
> skeleton — `--version` and `--help` respond, but the TUI isn't wired up yet.
> This README is the dev quickstart; the full user guide lands with v1.

---

## Prerequisites

Just [**uv**](https://docs.astral.sh/uv/). It manages the virtualenv *and* the
Python version for you — you don't need to install Python 3.11+ yourself.

```bash
brew install uv
```

---

## Quickstart

```bash
# From the project root:
make install        # create the venv + install everything (runtime + dev tools)
make run            # launch portpier
```

That's it. `uv` provisions Python 3.12 behind the scenes the first time.

---

## Common commands

Run `make` on its own to see this list any time:

```bash
make                # show all available commands
make install        # create venv + install deps (runtime + dev)
make run            # launch portpier
make version        # print the version
make typecheck      # mypy --strict on src/
make lint           # ruff lint on src/
make fmt            # auto-format + auto-fix with ruff
make test           # run the test suite
make check          # run everything: typecheck + lint + test
make clean          # nuke the venv and all caches
```

Prefer running things raw? Every target is a thin wrapper over `uv`:

```bash
uv run portpier --version
uv run mypy --strict src/
uv run ruff check src/
uv run pytest
```

---

## Install it globally (optional)

Want `portpier` on your PATH instead of `uv run portpier`?

```bash
uv tool install -e .
portpier --version       # → portpier 0.1.0
```

It's installed editable, so code changes are picked up without reinstalling.

---

## Project layout

```
src/portpier/
├── __main__.py     # CLI entry point
├── app.py          # root Textual app          (coming soon)
├── config.py       # TOML config               (coming soon)
├── data/           # psutil collection + models (coming soon)
├── ui/             # screens, widgets, themes   (coming soon)
└── utils/          # formatting, inference, signals (coming soon)
tests/              # pytest suite
```

The data layer (`src/portpier/data/`) is designed to be testable on its own,
with no Textual app required.

---

## Heads up

- `make test` shows "no tests collected yet" until the test suite arrives in the
  next phase — that's expected, not a failure.
- Config will live at `~/.config/portpier/config.toml` once the app runs (written
  only when you change a setting — nothing is created on a fresh install).
