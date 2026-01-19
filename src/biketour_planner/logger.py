"""Zentrales Logging-Modul für Bike Tour Planner.

Dieses Modul stellt einen konfigurierbaren Logger bereit, der sowohl
auf die Konsole als auch in Dateien schreiben kann.
"""

import logging
import sys

# import os
from pathlib import Path
from typing import Optional
from datetime import datetime

# Entferne die hartcodierte LOG_FILE Konstante
# LOG_FILE = Path(os.path.join("logs", f"app_{datetime.now().strftime('%Y%m%d_%H%M')}.log"))


def setup_logger(
    name: str = "biketour_planner",
    level: int = None,  # Geändert von logging.INFO
    log_file: Optional[Path] = None,
    console_output: bool = True,
) -> logging.Logger:
    """Konfiguriert und gibt einen Logger zurück.

    Args:
        name: Name des Loggers (Default: "biketour_planner").
        level: Logging-Level. Falls None, wird config.logging.level verwendet.
               Mögliche Werte: logging.DEBUG, logging.INFO, logging.WARNING,
               logging.ERROR, logging.CRITICAL.
        log_file: Optional. Pfad zur Log-Datei. Falls None, wird
                 config.logging.file verwendet.
        console_output: Wenn True, wird zusätzlich auf die Konsole geloggt.

    Returns:
        Konfigurierter Logger.

    Example:
        >>> logger = setup_logger()
        >>> logger.info("Starte Anwendung")
        >>>
        >>> # Mit Datei-Logging
        >>> logger = setup_logger(log_file=Path("logs/app.log"))
        >>> logger.debug("Debug-Information")
    """
    # Lade Config für Defaults (nur wenn benötigt)
    if level is None or log_file is None:
        from .config import get_config

        config = get_config()

        if level is None:
            # Konvertiere String zu logging Level
            level_str = config.logging.level.upper()
            level = getattr(logging, level_str, logging.INFO)

        if log_file is None:
            # Verwende Config-Pfad mit Timestamp
            base_log_path = Path(config.logging.file)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            log_file = base_log_path.parent / f"{base_log_path.stem}_{timestamp}.log"

    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Verhindere doppelte Handler wenn Logger mehrfach aufgerufen wird
    if logger.handlers:
        return logger

    # Format für Log-Nachrichten
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console Handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.WARNING)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # File Handler
    if log_file:
        # Erstelle Log-Verzeichnis falls nicht vorhanden
        log_file.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str = "biketour_planner") -> logging.Logger:
    """Gibt einen existierenden Logger zurück oder erstellt einen neuen.

    Diese Funktion ist für Module gedacht, die den bereits konfigurierten
    Logger verwenden möchten.

    Args:
        name: Name des Loggers (Default: "biketour_planner").

    Returns:
        Logger-Instanz.

    Example:
        >>> from biketour_planner.logger import get_logger
        >>> logger = get_logger()
        >>> logger.info("Nachricht")
    """
    logger = logging.getLogger(name)

    # Wenn Logger noch keine Handler hat, initialisiere mit Config-Werten
    if not logger.handlers:
        logger = setup_logger(name)  # level und log_file werden aus Config geladen

    return logger
