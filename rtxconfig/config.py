"""Configuration management for RTX config tool."""

import os
from pathlib import Path
from typing import Dict, Any, Optional
import logging

from pydantic import BaseModel, Field, validator
from ruamel.yaml import YAML

logger = logging.getLogger(__name__)


class RTXConnectionConfig(BaseModel):
    """RTX830 connection configuration."""
    host: str = Field(..., description="RTX830 IP address or hostname")
    username: str = Field(..., description="SSH username")
    key_file: str = Field(..., description="Path to SSH private key file")
    port: int = Field(22, description="SSH port")
    timeout: int = Field(30, description="Connection timeout in seconds")
    banner_timeout: int = Field(15, description="Banner timeout in seconds")
    auth_timeout: int = Field(15, description="Authentication timeout in seconds")
    conn_timeout: int = Field(10, description="Connection timeout in seconds")
    secret: Optional[str] = Field(None, description="Enable password for privileged mode")
    session_log: Optional[str] = Field(None, description="Path to session log file")
    
    @validator('key_file')
    def validate_key_file(cls, v):
        """Validate SSH key file path."""
        key_path = Path(v).expanduser()
        if not key_path.exists():
            logger.warning(f"SSH key file does not exist: {key_path}")
        return v
    
    @validator('port')
    def validate_port(cls, v):
        """Validate port number."""
        if not 1 <= v <= 65535:
            raise ValueError("Port must be between 1 and 65535")
        return v


class BackupConfig(BaseModel):
    """Backup configuration."""
    directory: str = Field("./backups", description="Backup directory path")
    keep_days: int = Field(30, description="Number of days to keep backups")
    
    @validator('keep_days')
    def validate_keep_days(cls, v):
        """Validate keep_days value."""
        if v <= 0:
            raise ValueError("keep_days must be positive")
        return v


class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str = Field("INFO", description="Log level")
    file: Optional[str] = Field(None, description="Log file path")
    
    @validator('level')
    def validate_level(cls, v):
        """Validate log level."""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v.upper()


class RTXConfig(BaseModel):
    """Main configuration class."""
    rtx_connection: RTXConnectionConfig
    backup: BackupConfig = BackupConfig()
    logging: LoggingConfig = LoggingConfig()
    
    class Config:
        """Pydantic config."""
        extra = "forbid"


class ConfigManager:
    """Configuration file manager."""
    
    def __init__(self, config_file: Optional[str] = None):
        """Initialize configuration manager.
        
        Args:
            config_file: Path to configuration file. If None, searches for default locations.
        """
        self.yaml = YAML()
        self.yaml.preserve_quotes = True
        self.yaml.width = 4096
        
        self.config_file = self._find_config_file(config_file)
        self.config: Optional[RTXConfig] = None
    
    def _find_config_file(self, config_file: Optional[str] = None) -> Optional[Path]:
        """Find configuration file in default locations.
        
        Args:
            config_file: Explicit config file path
            
        Returns:
            Path to config file or None if not found
        """
        if config_file:
            path = Path(config_file).expanduser()
            if path.exists():
                return path
            else:
                raise FileNotFoundError(f"Configuration file not found: {path}")
        
        # Search in default locations
        search_paths = [
            Path.cwd() / "config.yaml",
            Path.cwd() / "configs" / "config.yaml",
            Path.home() / ".rtxconfig" / "config.yaml",
            Path("/etc/rtxconfig/config.yaml"),
        ]
        
        for path in search_paths:
            if path.exists():
                logger.info(f"Found configuration file: {path}")
                return path
        
        logger.warning("No configuration file found in default locations")
        return None
    
    def load_config(self) -> RTXConfig:
        """Load configuration from file.
        
        Returns:
            Loaded configuration
            
        Raises:
            FileNotFoundError: If config file not found
            ValueError: If config file is invalid
        """
        if not self.config_file:
            raise FileNotFoundError("No configuration file specified or found")
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = self.yaml.load(f)
            
            if not data:
                raise ValueError("Configuration file is empty")
            
            self.config = RTXConfig(**data)
            logger.info(f"Configuration loaded from: {self.config_file}")
            return self.config
            
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found: {self.config_file}")
        except Exception as e:
            raise ValueError(f"Invalid configuration file: {e}")
    
    def save_config(self, config: RTXConfig, file_path: Optional[str] = None) -> None:
        """Save configuration to file.
        
        Args:
            config: Configuration to save
            file_path: Target file path. If None, uses current config file.
        """
        target_file = Path(file_path).expanduser() if file_path else self.config_file
        
        if not target_file:
            raise ValueError("No target file specified")
        
        # Ensure parent directory exists
        target_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(target_file, 'w', encoding='utf-8') as f:
                self.yaml.dump(config.model_dump(), f)
            
            logger.info(f"Configuration saved to: {target_file}")
            
        except Exception as e:
            raise ValueError(f"Failed to save configuration: {e}")
    
    def create_example_config(self, file_path: str) -> None:
        """Create example configuration file.
        
        Args:
            file_path: Path where to create example config
        """
        example_config = RTXConfig(
            rtx_connection=RTXConnectionConfig(
                host="192.168.1.1",
                username="admin",
                key_file="~/.ssh/rtx830_rsa"
            )
        )
        
        self.save_config(example_config, file_path)
        logger.info(f"Example configuration created at: {file_path}")
    
    def get_config(self) -> RTXConfig:
        """Get current configuration.
        
        Returns:
            Current configuration
            
        Raises:
            ValueError: If configuration not loaded
        """
        if not self.config:
            raise ValueError("Configuration not loaded. Call load_config() first.")
        return self.config


def load_config_from_file(config_file: Optional[str] = None) -> RTXConfig:
    """Convenience function to load configuration.
    
    Args:
        config_file: Path to configuration file
        
    Returns:
        Loaded configuration
    """
    manager = ConfigManager(config_file)
    return manager.load_config()