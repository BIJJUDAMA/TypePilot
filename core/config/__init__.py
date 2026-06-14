import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from core.logging import get_logger

logger = get_logger("core.config")

class ConfigLoader:
    """
    Loads and provides access to application configuration from YAML files.
    """
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the ConfigLoader.
        
        Args:
            config_path: Path to the YAML config file. If None, defaults to 
                        'config/app.yaml' relative to the project root.
        """
        if config_path is None:
            # Resolve default path relative to the project root (3 levels up from this file)
            project_root = Path(__file__).resolve().parent.parent.parent
            self.path = project_root / "config" / "app.yaml"
        else:
            self.path = Path(config_path).resolve()
            
        self.data: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        """
        Loads the YAML file from disk.
        
        Returns:
            Dictionary containing the configuration data.
            
        Raises:
            FileNotFoundError: If the config file does not exist.
            yaml.YAMLError: If the file contains invalid YAML.
        """
        if not self.path.exists():
            logger.error(f"Configuration file not found: {self.path}")
            raise FileNotFoundError(f"Required configuration file missing: {self.path}")
            
        try:
            with open(self.path, "r") as f:
                data = yaml.safe_load(f)
                if data is None:
                    logger.warning(f"Config file is empty: {self.path}")
                    return {}
                return data
        except yaml.YAMLError as e:
            logger.error(f"Failed to parse YAML configuration at {self.path}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error loading configuration at {self.path}: {e}")
            raise

    def get(self, key: str, default: Any = None) -> Any:
        """
        Retrieve a configuration value using dot notation (e.g., 'audio.sample_rate').
        
        Args:
            key: The configuration key.
            default: The value to return if the key is not found.
            
        Returns:
            The configuration value or the default.
        """
        parts = key.split(".")
        val = self.data
        for p in parts:
            if isinstance(val, dict) and p in val:
                val = val[p]
            else:
                return default
        return val
