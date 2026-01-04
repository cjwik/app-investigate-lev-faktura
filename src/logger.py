from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict

from . import config

_CONFIGURED = False


def _ensure_logs_dir() -> None:
    config.LOGS_DIR.mkdir(parents=True, exist_ok=True)


def setup_logger(name: str, log_file: str | Path, level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    if any(isinstance(h, RotatingFileHandler) and getattr(h, "baseFilename", None) == str(log_file) for h in logger.handlers):
        return logger

    _ensure_logs_dir()

    log_file = Path(log_file)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    logger.propagate = False
    return logger


def _configure_default_handlers() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    _ensure_logs_dir()

    root = logging.getLogger("investigationlevfaktura")
    root.setLevel(logging.DEBUG)

    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    main_handler = RotatingFileHandler(
        config.MAIN_LOG,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    main_handler.setLevel(logging.DEBUG)
    main_handler.setFormatter(formatter)

    error_handler = RotatingFileHandler(
        config.ERROR_LOG,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))

    root.addHandler(main_handler)
    root.addHandler(error_handler)
    root.addHandler(console_handler)
    root.propagate = False

    _CONFIGURED = True


def get_logger(module_name: str) -> logging.Logger:
    _configure_default_handlers()
    return logging.getLogger(f"investigationlevfaktura.{module_name}")


def log_processing_summary(stats: Dict[str, Any]) -> Path:
    config.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = config.REPORTS_DIR / "processing_summary.txt"

    lines = ["Processing Summary", ""]
    for key in sorted(stats.keys()):
        lines.append(f"{key}: {stats[key]}")
    lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path

