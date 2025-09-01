"""
This module contains the Config class which is used to load and get configuration data.
"""

import logging

import yaml


class Config:
    """
    This class is used to load and get configuration data.
    """

    def __init__(self, config_path: str) -> None:
        self.config = None
        self.config_path = config_path

    def load(self) -> None:
        """
        This method loads the configuration data from the specified path.
        """
        try:
            with open(self.config_path, encoding="utf-8") as f:
                self.config = yaml.safe_load(f)
        except FileNotFoundError as exc:
            logging.error("Config file not found: %s", exc)

    def get_config_of(self, key: str, default=None):
        """
        This method retrieves the configuration data for the given key.
        Supports nested keys with dot notation (e.g., "logging.level").
        """
        if self.config is None:
            self.load()
        if self.config is None:
            return default
            
        # Handle nested keys
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value
