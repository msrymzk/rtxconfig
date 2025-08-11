"""RTX830 configuration management functionality."""

import os
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import difflib
import logging

from .connection import RTXConnection, RTXConnectionError
from .config import RTXConfig

logger = logging.getLogger(__name__)


class ConfigManager:
    """Manages RTX830 configuration operations."""
    
    def __init__(self, config: RTXConfig):
        """Initialize configuration manager.
        
        Args:
            config: RTX configuration object
        """
        self.config = config
        self.backup_dir = Path(config.backup.directory).expanduser()
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def backup_config(self, connection: RTXConnection, suffix: str = "") -> Path:
        """Backup current RTX830 configuration.
        
        Args:
            connection: Active RTX connection
            suffix: Optional suffix for backup filename
            
        Returns:
            Path to backup file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"rtx830_config_{timestamp}"
        if suffix:
            filename += f"_{suffix}"
        filename += ".txt"
        
        backup_file = self.backup_dir / filename
        
        try:
            logger.info(f"Creating backup: {backup_file}")
            config_data = connection.get_running_config()
            
            with open(backup_file, 'w', encoding='utf-8') as f:
                f.write(config_data)
            
            logger.info(f"Backup created successfully: {backup_file}")
            return backup_file
            
        except Exception as e:
            raise RuntimeError(f"Failed to create backup: {e}")
    
    def apply_config(self, connection: RTXConnection, config_file: Path, 
                    create_backup: bool = True) -> Dict[str, Any]:
        """Apply configuration to RTX830.
        
        Args:
            connection: Active RTX connection
            config_file: Path to configuration file to apply
            create_backup: Whether to create backup before applying
            
        Returns:
            Dictionary with operation results
        """
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_file}")
        
        results = {
            'backup_file': None,
            'applied': False,
            'error': None
        }
        
        try:
            # Create backup if requested
            if create_backup:
                results['backup_file'] = self.backup_config(
                    connection, f"before_apply_{config_file.stem}"
                )
            
            # Read configuration commands
            with open(config_file, 'r', encoding='utf-8') as f:
                config_content = f.read()
            
            # Parse commands (skip comments and empty lines)
            commands = []
            for line in config_content.split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    commands.append(line)
            
            if not commands:
                raise ValueError("No valid configuration commands found")
            
            # Apply configuration
            logger.info(f"Applying {len(commands)} configuration commands")
            output = connection.send_config_commands(commands)
            
            # Save configuration
            save_output = connection.save_config()
            
            results['applied'] = True
            logger.info(f"Configuration applied successfully from: {config_file}")
            
        except Exception as e:
            results['error'] = str(e)
            logger.error(f"Failed to apply configuration: {e}")
            raise
        
        return results
    
    def get_config_diff(self, connection: RTXConnection, config_file: Path) -> str:
        """Compare current configuration with a file.
        
        Args:
            connection: Active RTX connection
            config_file: Path to configuration file to compare
            
        Returns:
            Unified diff string
        """
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_file}")
        
        # Get current configuration
        current_config = connection.get_running_config()
        
        # Read file configuration
        with open(config_file, 'r', encoding='utf-8') as f:
            file_config = f.read()
        
        # Generate diff
        current_lines = current_config.splitlines(keepends=True)
        file_lines = file_config.splitlines(keepends=True)
        
        diff = difflib.unified_diff(
            current_lines,
            file_lines,
            fromfile=f'Current RTX830 Config ({self.config.rtx_connection.host})',
            tofile=f'File Config ({config_file.name})',
            lineterm=''
        )
        
        return ''.join(diff)
    
    def restore_from_backup(self, connection: RTXConnection, backup_file: Path) -> bool:
        """Restore configuration from backup.
        
        Args:
            connection: Active RTX connection
            backup_file: Path to backup file
            
        Returns:
            True if restore successful
        """
        if not backup_file.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_file}")
        
        logger.info(f"Restoring configuration from: {backup_file}")
        
        # Create backup of current state before restore
        self.backup_config(connection, "before_restore")
        
        # Apply backup configuration
        results = self.apply_config(connection, backup_file, create_backup=False)
        
        if results['applied']:
            logger.info("Configuration restored successfully")
            return True
        else:
            logger.error(f"Failed to restore configuration: {results['error']}")
            return False
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """List all backup files.
        
        Returns:
            List of backup file information
        """
        backups = []
        
        for backup_file in self.backup_dir.glob("rtx830_config_*.txt"):
            try:
                stat = backup_file.stat()
                backups.append({
                    'file': backup_file,
                    'name': backup_file.name,
                    'size': stat.st_size,
                    'modified': datetime.fromtimestamp(stat.st_mtime),
                    'age_days': (datetime.now() - datetime.fromtimestamp(stat.st_mtime)).days
                })
            except Exception as e:
                logger.warning(f"Error reading backup file {backup_file}: {e}")
        
        # Sort by modification time (newest first)
        backups.sort(key=lambda x: x['modified'], reverse=True)
        
        return backups
    
    def cleanup_old_backups(self) -> int:
        """Remove old backup files based on keep_days setting.
        
        Returns:
            Number of files removed
        """
        if self.config.backup.keep_days <= 0:
            logger.info("Backup cleanup disabled (keep_days <= 0)")
            return 0
        
        cutoff_date = datetime.now() - timedelta(days=self.config.backup.keep_days)
        removed_count = 0
        
        for backup_file in self.backup_dir.glob("rtx830_config_*.txt"):
            try:
                file_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
                if file_time < cutoff_date:
                    backup_file.unlink()
                    removed_count += 1
                    logger.debug(f"Removed old backup: {backup_file}")
            except Exception as e:
                logger.warning(f"Error removing backup file {backup_file}: {e}")
        
        if removed_count > 0:
            logger.info(f"Removed {removed_count} old backup files")
        
        return removed_count
    
    def validate_config_file(self, config_file: Path) -> Dict[str, Any]:
        """Validate configuration file syntax.
        
        Args:
            config_file: Path to configuration file
            
        Returns:
            Validation results dictionary
        """
        results = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'command_count': 0
        }
        
        if not config_file.exists():
            results['valid'] = False
            results['errors'].append(f"File not found: {config_file}")
            return results
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            command_count = 0
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                command_count += 1
                
                # Basic validation (can be extended)
                if len(line) > 1000:  # Very long lines might be problematic
                    results['warnings'].append(
                        f"Line {line_num}: Very long command ({len(line)} chars)"
                    )
                
                # Check for potentially dangerous commands
                dangerous_patterns = ['format', 'erase', 'delete flash']
                for pattern in dangerous_patterns:
                    if pattern in line.lower():
                        results['warnings'].append(
                            f"Line {line_num}: Potentially dangerous command: {line}"
                        )
            
            results['command_count'] = command_count
            
            if command_count == 0:
                results['valid'] = False
                results['errors'].append("No valid configuration commands found")
            
        except Exception as e:
            results['valid'] = False
            results['errors'].append(f"Error reading file: {e}")
        
        return results