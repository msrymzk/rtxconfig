"""RTX830 SSH connection management."""

import os
import stat
from pathlib import Path
from typing import Optional, Dict, Any
import logging

from netmiko import ConnectHandler
from netmiko.exceptions import NetmikoBaseException, NetmikoTimeoutException, NetmikoAuthenticationException

logger = logging.getLogger(__name__)


class RTXConnectionError(Exception):
    """Custom exception for RTX connection errors."""
    pass


class RTXConnection:
    """Manages SSH connections to RTX830 devices."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize connection with configuration.
        
        Args:
            config: Connection configuration dictionary
        """
        self.config = config
        self.connection = None
        
        # Validate SSH key file
        self._validate_key_file()
    
    def _validate_key_file(self) -> None:
        """Validate SSH private key file exists and has proper permissions."""
        key_file = Path(self.config['key_file']).expanduser()
        
        if not key_file.exists():
            raise RTXConnectionError(f"SSH key file not found: {key_file}")
        
        # Check file permissions (should be 600 or 400)
        file_stat = key_file.stat()
        file_mode = stat.filemode(file_stat.st_mode)
        
        if file_stat.st_mode & 0o077:  # Check if group/other have permissions
            logger.warning(
                f"SSH key file {key_file} has overly permissive permissions: {file_mode}. "
                "Consider running: chmod 600 {key_file}"
            )
    
    def connect(self) -> None:
        """Establish SSH connection to RTX830."""
        if self.connection and self.connection.is_alive():
            return
        
        connection_params = {
            'device_type': 'yamaha',
            'host': self.config['host'],
            'username': self.config['username'],
            'use_keys': True,
            'key_file': str(Path(self.config['key_file']).expanduser()),
            'port': self.config.get('port', 22),
            'timeout': self.config.get('timeout', 30),
            'banner_timeout': self.config.get('banner_timeout', 15),
            'auth_timeout': self.config.get('auth_timeout', 15),
            'conn_timeout': self.config.get('conn_timeout', 10),
        }
        
        try:
            logger.info(f"Connecting to RTX830 at {self.config['host']}...")
            self.connection = ConnectHandler(**connection_params)
            logger.info("Successfully connected to RTX830")
            
        except NetmikoAuthenticationException as e:
            raise RTXConnectionError(f"Authentication failed: {e}")
        except NetmikoTimeoutException as e:
            raise RTXConnectionError(f"Connection timeout: {e}")
        except NetmikoBaseException as e:
            raise RTXConnectionError(f"Connection error: {e}")
        except Exception as e:
            raise RTXConnectionError(f"Unexpected error: {e}")
    
    def disconnect(self) -> None:
        """Close SSH connection."""
        if self.connection:
            try:
                self.connection.disconnect()
                logger.info("Disconnected from RTX830")
            except Exception as e:
                logger.warning(f"Error during disconnect: {e}")
            finally:
                self.connection = None
    
    def is_connected(self) -> bool:
        """Check if connection is active."""
        return self.connection is not None and self.connection.is_alive()
    
    def execute_command(self, command: str, expect_string: Optional[str] = None) -> str:
        """Execute command on RTX830.
        
        Args:
            command: Command to execute
            expect_string: Expected prompt after command execution
            
        Returns:
            Command output
            
        Raises:
            RTXConnectionError: If not connected or command fails
        """
        if not self.is_connected():
            raise RTXConnectionError("Not connected to RTX830")
        
        try:
            logger.debug(f"Executing command: {command}")
            output = self.connection.send_command(
                command,
                expect_string=expect_string,
                strip_prompt=True,
                strip_command=True
            )
            logger.debug(f"Command output length: {len(output)} chars")
            return output
            
        except NetmikoBaseException as e:
            raise RTXConnectionError(f"Command execution failed: {e}")
    
    def send_config_commands(self, commands: list[str]) -> str:
        """Send configuration commands to RTX830.
        
        Args:
            commands: List of configuration commands
            
        Returns:
            Combined output from all commands
        """
        if not self.is_connected():
            raise RTXConnectionError("Not connected to RTX830")
        
        try:
            logger.info(f"Sending {len(commands)} configuration commands")
            output = self.connection.send_config_set(commands)
            logger.info("Configuration commands sent successfully")
            return output
            
        except NetmikoBaseException as e:
            raise RTXConnectionError(f"Configuration failed: {e}")
    
    def get_running_config(self) -> str:
        """Get current running configuration.
        
        Returns:
            Current configuration as string
        """
        return self.execute_command("show config")
    
    def save_config(self) -> str:
        """Save current configuration to flash.
        
        Returns:
            Save command output
        """
        return self.execute_command("save")
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()


def create_connection(config: Dict[str, Any]) -> RTXConnection:
    """Factory function to create RTX connection.
    
    Args:
        config: Connection configuration
        
    Returns:
        RTXConnection instance
    """
    return RTXConnection(config)