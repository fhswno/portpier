"""Process-type inference from process names only.

Inference is process-name based — fast, no arg parsing, no filesystem
heuristics. See the coverage-limits note below for what this deliberately does
not detect.
"""

from __future__ import annotations

import os

PROCESS_TYPE_MAP: dict[str, str] = {
    # JavaScript runtimes
    "node": "Node.js",
    "deno": "Deno",
    "bun": "Bun",
    # Python — runtime names only; framework names (django, flask, fastapi) are
    # invoked via python/python3 and will NOT appear as process names
    "python": "Python",
    "python3": "Python",
    "uvicorn": "Uvicorn/ASGI",
    "gunicorn": "Gunicorn",
    "hypercorn": "Hypercorn",
    "granian": "Granian",
    # Ruby — note: rails/sinatra run under ruby or puma/unicorn, not their own names
    "ruby": "Ruby",
    "puma": "Puma",
    "unicorn": "Unicorn",
    # Java / JVM
    "java": "JVM",
    # Databases
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "mysqld": "MySQL",
    "redis-server": "Redis",
    "mongod": "MongoDB",
    "elasticsearch": "Elasticsearch",
    # Web servers / proxies
    "nginx": "Nginx",
    "apache2": "Apache",
    "httpd": "Apache",
    "caddy": "Caddy",
    "traefik": "Traefik",
    # PHP
    "php": "PHP",
    "php-fpm": "PHP-FPM",
    # Misc — note: compiled Go/Rust binaries have arbitrary names; only the
    # toolchain binaries are listed here, which are rarely servers
    "mintlify": "Mintlify",
}
# NOTE ON COVERAGE LIMITS:
# Name-only inference was chosen explicitly for speed. It will not detect:
# - Go servers (go run spawns a temp binary; compiled binaries have arbitrary names)
# - Rust servers (cargo run / compiled binaries same situation)
# - Django/Flask/Rails (invoked as python3/ruby, framework name never appears)
# This is a known, accepted tradeoff. The TYPE column shows "—" for unrecognised names.


def infer_process_type(process_name: str | None) -> str | None:
    """Map a raw process name to a human-readable label.

    Looks up ``process_name`` (lowercased, basename only) in
    ``PROCESS_TYPE_MAP``. Returns the label, or ``None`` if not recognised.
    Never raises.
    """
    if process_name is None:
        return None
    name = os.path.basename(process_name).lower()
    return PROCESS_TYPE_MAP.get(name)
