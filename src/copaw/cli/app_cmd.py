# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
import os
from pathlib import Path

import click
import uvicorn
from dotenv import load_dotenv

from ..constant import LOG_LEVEL_ENV
from ..config.utils import write_last_api
from ..utils.logging import setup_logger, SuppressPathAccessLogFilter


def _load_app_dotenv() -> None:
    """Load ``.env`` from cwd and ``COPAW_WORKING_DIR``; shell exports win."""
    candidates = [
        Path.cwd() / ".env",
        Path(os.environ.get("COPAW_WORKING_DIR", "~/.copaw")).expanduser() / ".env",
    ]
    seen: set[Path] = set()
    for path in candidates:
        try:
            resolved = path.resolve()
        except OSError:
            continue
        if resolved in seen or not resolved.is_file():
            continue
        seen.add(resolved)
        load_dotenv(resolved, override=False)


@click.command("app")
@click.option(
    "--host",
    default="127.0.0.1",
    show_default=True,
    help="Bind host",
)
@click.option(
    "--port",
    default=8088,
    type=int,
    show_default=True,
    help="Bind port",
)
@click.option("--reload", is_flag=True, help="Enable auto-reload (dev only)")
@click.option(
    "--workers",
    default=1,
    type=int,
    show_default=True,
    help="Worker processes",
)
@click.option(
    "--log-level",
    default="info",
    type=click.Choice(
        ["critical", "error", "warning", "info", "debug", "trace"],
        case_sensitive=False,
    ),
    show_default=True,
    help="Log level",
)
@click.option(
    "--hide-access-paths",
    multiple=True,
    default=("/console/push-messages",),
    show_default=True,
    help="Path substrings to hide from uvicorn access log (repeatable).",
)
@click.option(
    "--reload-exclude",
    multiple=True,
    default=(),
    help="Glob(s) excluded from reload watch (repeatable; dev only).",
)
def app_cmd(
    host: str,
    port: int,
    reload: bool,
    workers: int,
    log_level: str,
    hide_access_paths: tuple[str, ...],
    reload_exclude: tuple[str, ...],
) -> None:
    """Run CoPaw FastAPI app."""
    _load_app_dotenv()
    # Persist last used host/port for other terminals
    write_last_api(host, port)
    os.environ[LOG_LEVEL_ENV] = log_level

    # Signal reload mode to browser_control.py for Windows
    # compatibility: use sync Playwright + ThreadPool only when reload=True
    if reload:
        os.environ["COPAW_RELOAD_MODE"] = "1"
    else:
        os.environ.pop("COPAW_RELOAD_MODE", None)

    setup_logger(log_level)
    if log_level in ("debug", "trace"):
        from .main import log_init_timings

        log_init_timings()

    paths = [p for p in hide_access_paths if p]
    if paths:
        logging.getLogger("uvicorn.access").addFilter(
            SuppressPathAccessLogFilter(paths),
        )

    uvicorn.run(
        "copaw.app._app:app",
        host=host,
        port=port,
        reload=reload,
        reload_excludes=list(reload_exclude) if reload_exclude else None,
        workers=workers,
        log_level=log_level,
    )
