from __future__ import annotations

import logging
import sys


def configure_logging(env: str = "local") -> None:
    """Configure logging for OpenDove.

    In non-local environments, emits JSON lines suitable for log aggregation.
    Locally, emits human-readable text.
    """
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    # Remove any handlers already attached (e.g. from uvicorn)
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)

    if env != "local":
        try:
            from pythonjsonlogger.json import JsonFormatter  # type: ignore[import-untyped]

            formatter = JsonFormatter(
                fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
                rename_fields={"asctime": "ts", "name": "logger", "levelname": "level"},
            )
        except ImportError:
            # python-json-logger not installed — fall back to plain text
            formatter = logging.Formatter(
                fmt="%(asctime)s %(name)-20s %(levelname)-8s %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S",
            )
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s %(name)-20s %(levelname)-8s %(message)s",
            datefmt="%H:%M:%S",
        )

    handler.setFormatter(formatter)
    root.addHandler(handler)

    # Quiet noisy third-party loggers
    for noisy in ("httpx", "httpcore", "langchain", "openai", "anthropic"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
