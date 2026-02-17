"""Configuration management for the Bike Tour Planner.

Loads configuration from a YAML file with fallback to default values.
"""

from pathlib import Path
from typing import Any

import yaml


class Config:
    """Central configuration class.

    Loads configuration from config.yaml or uses defaults.

    Example:
        >>> config = Config()
        >>> print(config.get("routing.max_connection_distance_m"))
        1000
        >>> print(config.directories.gpx)
        PosixPath('../2026_Croatia/gpx')
    """

    DEFAULT_CONFIG = {
        "directories": {"booking": "../bookings", "gpx": "../gpx", "output": "../output"},
        "routing": {
            "brouter_url": "http://localhost:17777",
            "max_connection_distance_m": 1000,
            "max_chain_length": 20,
            "start_search_radius_km": 3.0,
            "target_search_radius_km": 10.0,
        },
        "passes": {"hotel_radius_km": 5.0, "pass_radius_km": 5.0, "passes_file": "Paesse.json"},
        "geoapify": {"search_radius_m": 5000, "max_pois": 2},
        "export": {"title": "Bike Tour", "excel_info_file": "Reiseplanung_Fahrrad.xlsx"},
        "logging": {"level": "INFO", "file": "logs/app.log"},
    }

    def __init__(self, config_path: Path = Path("config.yaml")):
        """Initializes configuration.

        Args:
            config_path: Path to the YAML configuration file (Default: config.yaml).
        """
        self._config = self.DEFAULT_CONFIG.copy()

        if config_path.exists():
            with open(config_path, encoding="utf-8") as f:
                user_config = yaml.safe_load(f)
                self._merge_config(user_config)
        else:
            print(f"⚠️  No {config_path} found, using default configuration")

    def _merge_config(self, user_config: dict[str, Any]) -> None:
        """Merges user config with defaults (Deep Merge).

        Args:
            user_config: Dictionary containing user-defined configuration values.
        """

        def deep_merge(base: dict, override: dict) -> dict:
            """Recursively merges two dictionaries."""
            result = base.copy()
            for key, value in override.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = deep_merge(result[key], value)
                else:
                    result[key] = value
            return result

        self._config = deep_merge(self._config, user_config)

    def get(self, key: str, default: Any = None) -> Any:
        """Gets a configuration value using dot notation.

        Args:
            key: Configuration key in dot notation (e.g., "routing.max_connection_distance_m").
            default: Return value if the key does not exist.

        Returns:
            The configuration value or the default.

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
        """Access directory configuration."""
        return DirectoriesConfig(self._config["directories"])

    @property
    def routing(self) -> "RoutingConfig":
        """Access routing configuration."""
        return RoutingConfig(self._config["routing"])

    @property
    def passes(self) -> "PassesConfig":
        """Access mountain pass finder configuration."""
        return PassesConfig(self._config["passes"])

    @property
    def geoapify(self) -> "GeoapifyConfig":
        """Access Geoapify configuration."""
        return GeoapifyConfig(self._config["geoapify"])

    @property
    def export(self) -> "ExportConfig":
        """Access export configuration."""
        return ExportConfig(self._config["export"])

    @property
    def logging(self) -> "LoggingConfig":
        """Access logging configuration."""
        return LoggingConfig(self._config["logging"])


class DirectoriesConfig:
    """Helper class for directory configuration access."""

    def __init__(self, config: dict):
        """Initializes DirectoriesConfig.

        Args:
            config: Dictionary containing directory settings.
        """
        self._config = config

    @property
    def booking(self) -> Path:
        """Path to booking HTML files."""
        return Path(self._config["booking"])

    @property
    def gpx(self) -> Path:
        """Path to original GPX files."""
        return Path(self._config["gpx"])

    @property
    def output(self) -> Path:
        """Path for generated output files."""
        return Path(self._config["output"])


class RoutingConfig:
    """Helper class for routing parameters."""

    def __init__(self, config: dict):
        """Initializes RoutingConfig.

        Args:
            config: Dictionary containing routing settings.
        """
        self._config = config

    @property
    def brouter_url(self) -> str:
        """URL of the BRouter engine."""
        return self._config["brouter_url"]

    @property
    def max_connection_distance_m(self) -> float:
        """Maximum distance for automatic track chaining in meters."""
        return float(self._config["max_connection_distance_m"])

    @property
    def max_chain_length(self) -> int:
        """Maximum number of tracks to chain."""
        return int(self._config["max_chain_length"])

    @property
    def start_search_radius_km(self) -> float:
        """Search radius for the start track in kilometers."""
        return float(self._config["start_search_radius_km"])

    @property
    def target_search_radius_km(self) -> float:
        """Search radius for the target track in kilometers."""
        return float(self._config.get("target_search_radius_km", 10.0))


class PassesConfig:
    """Helper class for mountain pass finder parameters."""

    def __init__(self, config: dict):
        """Initializes PassesConfig.

        Args:
            config: Dictionary containing pass finder settings.
        """
        self._config = config

    @property
    def hotel_radius_km(self) -> float:
        """Search radius around hotels for passes in kilometers."""
        return float(self._config["hotel_radius_km"])

    @property
    def pass_radius_km(self) -> float:
        """Search radius around pass summits in kilometers."""
        return float(self._config["pass_radius_km"])

    @property
    def passes_file(self) -> str:
        """Filename of the JSON pass database."""
        return self._config["passes_file"]


class GeoapifyConfig:
    """Helper class for Geoapify parameters."""

    def __init__(self, config: dict):
        """Initializes GeoapifyConfig.

        Args:
            config: Dictionary containing Geoapify settings.
        """
        self._config = config

    @property
    def search_radius_m(self) -> int:
        """Search radius for tourist attractions in meters."""
        return int(self._config["search_radius_m"])

    @property
    def max_pois(self) -> int:
        """Maximum number of tourist attractions to discover."""
        return int(self._config["max_pois"])


class ExportConfig:
    """Helper class for export parameters."""

    def __init__(self, config: dict):
        """Initializes ExportConfig.

        Args:
            config: Dictionary containing export settings.
        """
        self._config = config

    @property
    def title(self) -> str:
        """Title of the generated report."""
        return self._config["title"]

    @property
    def excel_info_file(self) -> str:
        """Filename of the additional trip info Excel file."""
        return self._config["excel_info_file"]


class LoggingConfig:
    """Helper class for logging parameters."""

    def __init__(self, config: dict):
        """Initializes LoggingConfig.

        Args:
            config: Dictionary containing logging settings.
        """
        self._config = config

    @property
    def level(self) -> str:
        """Logging level (e.g., 'INFO', 'DEBUG')."""
        return self._config["level"]

    @property
    def file(self) -> str:
        """Path to the log file."""
        return self._config["file"]


# Global config instance
_global_config: Config = None


def get_config() -> Config:
    """Gets the global configuration instance (Singleton).

    Returns:
        The Config instance.
    """
    global _global_config
    if _global_config is None:
        _global_config = Config()
    return _global_config
