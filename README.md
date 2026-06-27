# portpier

> A gorgeous, keyboard-driven TUI dashboard for monitoring and managing ports on macOS.
> Built with Python + Textual + psutil. System ports (< 1024) are always hidden.

`portpier` shows every active user-space socket (all states) with full process
metadata, a live-updating table, one-keypress process termination, a rich detail
view, and a command palette — all driven by `psutil` (no `lsof`/`netstat`).

---

## Prerequisites

Just [**uv**](https://docs.astral.sh/uv/). It provisions the virtualenv *and* the
Python version — no need to install Python 3.11+ yourself.

```bash
brew install uv
```

## Install

Run it from the checkout, or install it globally on your PATH:

```bash
# From the project root:
make install        # create the venv + install everything (runtime + dev tools)
make run            # launch portpier

# …or, globally (editable — code changes are picked up without reinstalling):
uv tool install -e .
portpier
```

---

## Keyboard reference

### Main dashboard

| Key | Action |
|---|---|
| `↑` / `↓` | Move row selection |
| `Enter` | Open the detail view for the selected process |
| `k` | Kill the selected process (opens the confirm dialog) |
| `/` | Focus the search box |
| `s` | Cycle the sort column |
| `Esc` | Clear the search |
| `Ctrl+P` | Open the command palette |
| `t` | Cycle theme |
| `r` | Force an immediate data refresh |
| `q` / `Ctrl+Q` | Quit |
| Click a row | Select it |
| Click a column header | Sort by that column (toggle asc/desc) |

Search filters client-side (case-insensitive substring) across port, process
name, type, state, and PID. The status bar shows the live match count.

### Detail view

| Key | Action |
|---|---|
| `Esc` / `q` | Return to the dashboard (same row stays selected) |
| `k` | Kill this process (opens the confirm dialog; returns to the dashboard on success) |
| `↑` / `↓` | Scroll the detail content |

### Kill dialog

| Key | Action |
|---|---|
| `Tab` / `←` `→` `↑` `↓` | Move between Graceful / Force Kill / Cancel |
| `Enter` | Activate the focused button (Graceful = SIGTERM, Force = SIGKILL) |
| `Esc` | Cancel / dismiss (no action) |

---

## Command palette (`Ctrl+P`)

| Command | Action |
|---|---|
| `theme <name>` | Switch theme — `dark`, `light`, `paper`, or `matrix` |
| `toggle <column>` | Show/hide a column (e.g. `toggle pid`). `PORT` is always visible. |
| `sort <column> [asc\|desc]` | Sort by `port`, `memory`, `cpu`, or `uptime` |
| `refresh <seconds>` | Set the refresh interval (0.5–60) |
| `port range <min> [max]` | Filter to a port range (e.g. `port range 3000 9999`) |
| `port range reset` | Clear the port-range filter (back to 1024–65535) |
| `help` | Show the command reference |

Every change is persisted immediately to the config file (below).

---

## Themes

| Name | Look |
|---|---|
| `dark` | Default. Dark canvas, high contrast, purple accent. |
| `light` | Clean light mode for daytime/bright terminals. |
| `paper` | Stark black on white — print-like, minimal. |
| `matrix` | Green-on-black, monospace terminal aesthetic. |

---

## Configuration

Config lives at `~/.config/portpier/config.toml`. It is created the first time
you change a setting (via the palette); a fresh install runs entirely on
defaults. To reset, just delete the file.

```toml
schema_version = 1

[display]
theme = "dark"                       # "dark" | "light" | "paper" | "matrix"
refresh_interval = 2.0               # seconds; clamped to [0.5, 60.0]
columns = ["port", "process", "type", "pid", "memory", "cpu", "state", "uptime"]
default_sort_column = "port"         # "port" | "memory" | "cpu" | "uptime"
default_sort_order = "asc"           # "asc" | "desc"

[filters]
min_port = 1024                      # hard floor: never below 1024
max_port = 65535
```

Unknown keys are ignored. An unknown/missing `schema_version` falls back to
defaults with a warning. `min_port` is always floored to `1024`.

---

## Notes

- **Without `sudo`:** processes you own are fully visible. Other users'
  processes raise `AccessDenied` and don't appear; the status bar then shows
  `⚠ Some processes require sudo to inspect`.
- **With `sudo`:** all processes are visible and the warning is absent.
- macOS sandboxes `open_files()` / `environ()`, so the detail view's
  **Open FDs** and **Environment** sections are often empty without `sudo` —
  this is expected, not a bug.

---

## Project layout

```
src/portpier/
├── __main__.py     # CLI entry point (--version / --help / launch)
├── app.py          # root Textual app
├── config.py       # TOML config (load/save, validation, atomic write)
├── data/           # psutil collection + immutable models
├── ui/             # screens, widgets, themes, command palette
└── utils/          # formatting, process-type inference, signals
tests/              # pytest suite (data layer + parsers + signals)
```

The data layer is fully testable without instantiating a Textual app.

## Common commands

```bash
make                # list all targets
make check          # typecheck + lint + test
make typecheck      # mypy --strict on src/
make lint           # ruff lint on src/
make fmt            # auto-format + auto-fix with ruff
make test           # run the test suite
make smoke          # live data-layer check against real ports
make clean          # remove the venv and all caches
```
