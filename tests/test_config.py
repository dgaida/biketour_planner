import pytest
import yaml
from pathlib import Path
from biketour_planner.config import Config, get_config

def test_config_default():
    config = Config(Path("nonexistent.yaml"))
    assert config.routing.brouter_url == "http://localhost:17777"
    assert config.geoapify.max_pois == 2

def test_config_override(tmp_path):
    config_file = tmp_path / "config.yaml"
    user_config = {
        "routing": {
            "brouter_url": "http://other-host:18888",
            "max_connection_distance_m": 2000
        },
        "geoapify": {
            "max_pois": 5
        }
    }
    with open(config_file, "w") as f:
        yaml.dump(user_config, f)

    config = Config(config_file)
    assert config.routing.brouter_url == "http://other-host:18888"
    assert config.routing.max_connection_distance_m == 2000.0
    assert config.geoapify.max_pois == 5
    # Default values preserved
    assert config.geoapify.search_radius_m == 5000

def test_config_get():
    config = Config()
    assert config.get("routing.brouter_url") == "http://localhost:17777"
    assert config.get("nonexistent.key", "default") == "default"
    assert config.get("routing.missing", "default") == "default"

def test_config_properties():
    config = Config()
    assert isinstance(config.directories.booking, Path)
    assert isinstance(config.directories.gpx, Path)
    assert isinstance(config.directories.output, Path)
    assert isinstance(config.routing.max_chain_length, int)
    assert isinstance(config.routing.start_search_radius_km, float)
    assert isinstance(config.routing.target_search_radius_km, float)
    assert isinstance(config.passes.hotel_radius_km, float)
    assert isinstance(config.passes.pass_radius_km, float)
    assert isinstance(config.passes.passes_file, str)
    assert isinstance(config.geoapify.search_radius_m, int)
    assert isinstance(config.export.title, str)
    assert isinstance(config.export.excel_info_file, str)
    assert isinstance(config.logging.level, str)
    assert isinstance(config.logging.file, str)

def test_get_config_singleton():
    c1 = get_config()
    c2 = get_config()
    assert c1 is c2
