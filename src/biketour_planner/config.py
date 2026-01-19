"""Konfigurations-Management für Bike Tour Planner.

Lädt Konfiguration aus YAML-Datei mit Fallback auf Default-Werte.
"""

from pathlib import Path
from typing import Any

import yaml


class Config:
    """Zentrale Konfigurations-Klasse.

    Lädt Konfiguration aus config.yaml oder verwendet Defaults.

    Example:
        >>> config = Config()
        >>> print(config.get("routing.max_connection_distance_m"))
        1000
        >>> print(config.directories.gpx)
        PosixPath('../2026_Kroatien/gpx')
    """

    DEFAULT_CONFIG = {
        "directories": {"booking": "../bookings", "gpx": "../gpx", "output": "../output"},
        "routing": {
            "brouter_url": "http://localhost:17777",
            "max_connection_distance_m": 1000,
            "max_chain_length": 20,
            "start_search_radius_km": 3.0,
        },
        "passes": {"hotel_radius_km": 5.0, "pass_radius_km": 5.0, "passes_file": "Paesse.json"},
        "geoapify": {"search_radius_m": 5000, "max_pois": 2},
        "export": {"title": "Bike Tour", "excel_info_file": "Reiseplanung_Fahrrad.xlsx"},
        "logging": {"level": "INFO", "file": "logs/app.log"},
    }

    def __init__(self, config_path: Path = Path("config.yaml")):
        """Initialisiert Konfiguration.

        Args:
            config_path: Pfad zur YAML-Konfigurationsdatei (Default: config.yaml).
        """
        self._config = self.DEFAULT_CONFIG.copy()

        if config_path.exists():
            with open(config_path, encoding="utf-8") as f:
                user_config = yaml.safe_load(f)
                self._merge_config(user_config)
        else:
            print(f"⚠️  Keine {config_path} gefunden, verwende Default-Konfiguration")

    def _merge_config(self, user_config: dict[str, Any]) -> None:
        """Merged User-Config mit Defaults (Deep Merge)."""

        def deep_merge(base: dict, override: dict) -> dict:
            result = base.copy()
            for key, value in override.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = deep_merge(result[key], value)
                else:
                    result[key] = value
            return result

        self._config = deep_merge(self._config, user_config)

    def get(self, key: str, default: Any = None) -> Any:
        """Holt Konfigurations-Wert mit Dot-Notation.

        Args:
            key: Konfigurations-Key in Dot-Notation (z.B. "routing.max_connection_distance_m").
            default: Rückgabewert falls Key nicht existiert.

        Returns:
            Konfigurations-Wert oder default.

        Example:
            >>> config = Config()
            >>> config.get("routing.brouter_url")
            'http://localhost:17777'
        """
        keys = key.split(".")
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    @property
    def directories(self) -> "DirectoriesConfig":
        """Zugriff auf Verzeichnis-Konfiguration."""
        return DirectoriesConfig(self._config["directories"])

    @property
    def routing(self) -> "RoutingConfig":
        """Zugriff auf Routing-Konfiguration."""
        return RoutingConfig(self._config["routing"])


class DirectoriesConfig:
    """Helper-Klasse für Verzeichnis-Zugriffe."""

    def __init__(self, config: dict):
        self._config = config

    @property
    def booking(self) -> Path:
        return Path(self._config["booking"])

    @property
    def gpx(self) -> Path:
        return Path(self._config["gpx"])

    @property
    def output(self) -> Path:
        return Path(self._config["output"])


class RoutingConfig:
    """Helper-Klasse für Routing-Parameter."""

    def __init__(self, config: dict):
        self._config = config

    @property
    def brouter_url(self) -> str:
        return self._config["brouter_url"]

    @property
    def max_connection_distance_m(self) -> float:
        return float(self._config["max_connection_distance_m"])

    @property
    def max_chain_length(self) -> int:
        return int(self._config["max_chain_length"])


# Globale Config-Instanz
_global_config: Config = None


def get_config() -> Config:
    """Holt globale Konfigurations-Instanz (Singleton).

    Returns:
        Config-Instanz.
    """
    global _global_config
    if _global_config is None:
        _global_config = Config()
    return _global_config
