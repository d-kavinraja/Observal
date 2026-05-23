# SPDX-FileCopyrightText: 2026 Shaan Narendran <shaannaren06@gmail.com>
# SPDX-License-Identifier: AGPL-3.0-only

"""Optic: developer debug logging for Observal.

Configures loguru sinks based on deployment mode. Call ``setup_optic()``
once at server startup. Then use ``from loguru import logger`` anywhere
in the codebase to log actions.

Terminal (stderr) gets INFO+ only to keep output clean.
File (~/.observal/logs/dev.log) gets full DEBUG trace.
Production gets INFO+ with plain formatting (no colors).
"""

from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger


def setup_optic(*, mode: str = "local", level: str = "DEBUG") -> None:
    """Configure loguru sinks based on deployment mode.

    Args:
        mode: Deployment mode ("local" or "enterprise").
        level: Minimum log level for file sink (default: DEBUG).
    """
    # Remove loguru's default stderr sink
    logger.remove()

    if mode == "local":
        # Console: INFO+ only to avoid clogging the terminal
        logger.add(
            sys.stderr,
            level="INFO",
            colorize=True,
            format=(
                "<green>{time:HH:mm:ss.SSS}</green> | "
                "<level>{level:<7}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
                "<level>{message}</level>"
            ),
        )
        # File: full DEBUG trace for post-mortem debugging
        # Skip gracefully if home dir is read-only (e.g. Docker containers)
        try:
            log_path = Path.home() / ".observal" / "logs" / "dev.log"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            logger.add(
                str(log_path),
                rotation="10 MB",
                retention=5,
                level=level,
                format=("{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<7} | {name}:{function}:{line} - {message}"),
            )
        except OSError:
            pass
    else:
        # Production: INFO+ to stderr, plain format (JSON handled by structlog)
        logger.add(
            sys.stderr,
            level="INFO",
            colorize=False,
            format="{time:YYYY-MM-DDTHH:mm:ss.SSSZ} | {level:<7} | {name}:{function} - {message}",
        )
