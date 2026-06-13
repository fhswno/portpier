"""The four portpier themes.

``TOKENS`` is the single source of truth for every colour. From it we build the
Textual ``Theme`` objects (used for widget/CSS styling) and also resolve the
STATE-column colours directly (Rich Text needs concrete hex values).
"""

from __future__ import annotations

from textual.theme import Theme

TOKENS: dict[str, dict[str, str]] = {
    "dark": {
        "background": "#0d0d0d",
        "surface": "#161616",
        "panel": "#1e1e1e",
        "border": "#2a2a2a",
        "text": "#e8e8e8",
        "text-muted": "#666666",
        "accent": "#7c6ef7",
        "accent-hover": "#9d93f9",
        "row-selected": "#2a2560",
        "row-hover": "#1a1a2e",
        "state-listen": "#4ade80",
        "state-established": "#60a5fa",
        "state-timewait": "#f59e0b",
        "state-closewait": "#f87171",
        "state-other": "#a1a1aa",
        "memory-bar-fill": "#7c6ef7",
        "cpu-bar-fill": "#f59e0b",
        "danger": "#ef4444",
        "header-bg": "#111111",
    },
    "light": {
        "background": "#f5f5f5",
        "surface": "#ffffff",
        "panel": "#ebebeb",
        "border": "#d4d4d4",
        "text": "#111111",
        "text-muted": "#888888",
        "accent": "#5b4fcf",
        "accent-hover": "#7b70e8",
        "row-selected": "#e0deff",
        "row-hover": "#f0eeff",
        "state-listen": "#16a34a",
        "state-established": "#2563eb",
        "state-timewait": "#d97706",
        "state-closewait": "#dc2626",
        "state-other": "#71717a",
        "memory-bar-fill": "#5b4fcf",
        "cpu-bar-fill": "#d97706",
        "danger": "#dc2626",
        "header-bg": "#e8e8e8",
    },
    "paper": {
        "background": "#ffffff",
        "surface": "#f9f9f9",
        "panel": "#f0f0f0",
        "border": "#cccccc",
        "text": "#0a0a0a",
        "text-muted": "#555555",
        "accent": "#1a1a1a",
        "accent-hover": "#333333",
        "row-selected": "#e8e8e8",
        "row-hover": "#f4f4f4",
        "state-listen": "#1a1a1a",
        "state-established": "#333333",
        "state-timewait": "#555555",
        "state-closewait": "#777777",
        "state-other": "#888888",
        "memory-bar-fill": "#333333",
        "cpu-bar-fill": "#555555",
        "danger": "#111111",
        "header-bg": "#eeeeee",
    },
    "matrix": {
        "background": "#000000",
        "surface": "#0a0a0a",
        "panel": "#111111",
        "border": "#1a3a1a",
        "text": "#00cc44",
        "text-muted": "#006622",
        "accent": "#00ff55",
        "accent-hover": "#33ff77",
        "row-selected": "#003311",
        "row-hover": "#001a08",
        "state-listen": "#00ff55",
        "state-established": "#00aaff",
        "state-timewait": "#aaaa00",
        "state-closewait": "#ff4444",
        "state-other": "#448844",
        "memory-bar-fill": "#00cc44",
        "cpu-bar-fill": "#aaff00",
        "danger": "#ff2222",
        "header-bg": "#050505",
    },
}

_DARK_THEMES = {"dark", "matrix"}

THEME_NAMES = ["dark", "light", "paper", "matrix"]

_STATE_TOKEN = {
    "LISTEN": "state-listen",
    "ESTABLISHED": "state-established",
    "TIME_WAIT": "state-timewait",
    "CLOSE_WAIT": "state-closewait",
}


def _build_theme(name: str) -> Theme:
    tokens = TOKENS[name]
    return Theme(
        name=name,
        primary=tokens["accent"],
        secondary=tokens["accent-hover"],
        accent=tokens["accent"],
        foreground=tokens["text"],
        background=tokens["background"],
        surface=tokens["surface"],
        panel=tokens["panel"],
        success=tokens["state-listen"],
        warning=tokens["state-timewait"],
        error=tokens["danger"],
        dark=name in _DARK_THEMES,
        variables=dict(tokens),
    )


THEMES: dict[str, Theme] = {name: _build_theme(name) for name in THEME_NAMES}


def state_color(theme_name: str, state: str) -> str:
    """Resolve the hex colour for a socket ``state`` under ``theme_name``."""
    tokens = TOKENS.get(theme_name, TOKENS["dark"])
    return tokens[_STATE_TOKEN.get(state, "state-other")]
