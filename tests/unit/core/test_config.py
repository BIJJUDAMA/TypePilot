import pytest
import os
import yaml
from pathlib import Path
from core.config import ConfigLoader

def test_config_loader_load_custom_path(tmp_path):
    # Setup a dummy config file
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_file = config_dir / "app.yaml"
    
    config_data = {
        "audio": {
            "sample_rate": 16000
        },
        "whisper": {
            "model": "small"
        }
    }
    
    with open(config_file, "w") as f:
        yaml.dump(config_data, f)
        
    # Initialize loader with temp path
    cfg = ConfigLoader(config_path=str(config_file))
    
    assert cfg.get("audio.sample_rate") == 16000
    assert cfg.get("whisper.model") == "small"
    assert cfg.get("nonexistent.key", "default") == "default"

def test_config_loader_missing_file():
    with pytest.raises(FileNotFoundError):
        ConfigLoader(config_path="nonexistent_config.yaml")

def test_config_loader_malformed_yaml(tmp_path):
    config_file = tmp_path / "malformed.yaml"
    with open(config_file, "w") as f:
        f.write("invalid: yaml: :")
        
    with pytest.raises(yaml.YAMLError):
        ConfigLoader(config_path=str(config_file))

def test_config_loader_empty_file(tmp_path):
    config_file = tmp_path / "empty.yaml"
    with open(config_file, "w") as f:
        f.write("")
        
    cfg = ConfigLoader(config_path=str(config_file))
    assert cfg.data == {}

def test_config_loader_nested_get(tmp_path):
    config_file = tmp_path / "nested.yaml"
    data = {"a": {"b": {"c": 1}}}
    with open(config_file, "w") as f:
        yaml.dump(data, f)
        
    cfg = ConfigLoader(config_path=str(config_file))
    assert cfg.get("a.b.c") == 1
    assert cfg.get("a.b") == {"c": 1}
    assert cfg.get("a.x") is None
