"""Command line interface for RTX config management."""

import sys
import logging
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.columns import Columns

from .config import ConfigManager as ConfigFileManager, RTXConfig
from .connection import create_connection, RTXConnectionError
from .manager import ConfigManager

console = Console()


def setup_logging(level: str = "INFO", log_file: Optional[str] = None):
    """Setup logging configuration."""
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    handlers = [logging.StreamHandler()]
    if log_file:
        log_path = Path(log_file).expanduser()
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_path))
    
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=log_format,
        handlers=handlers
    )


@click.group()
@click.option(
    "--config", "-c",
    type=click.Path(exists=True, path_type=Path),
    help="Configuration file path"
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Enable verbose logging"
)
@click.pass_context
def main(ctx, config: Optional[Path], verbose: bool):
    """RTX830 configuration management tool."""
    ctx.ensure_object(dict)
    ctx.obj['config_file'] = config
    ctx.obj['verbose'] = verbose
    
    # Don't load configuration for init-config command
    if ctx.invoked_subcommand == 'init-config':
        return
    
    # Load configuration for other commands
    try:
        config_manager = ConfigFileManager(str(config) if config else None)
        rtx_config = config_manager.load_config()
        ctx.obj['config'] = rtx_config
        ctx.obj['config_manager'] = config_manager
        
        # Setup logging
        log_level = "DEBUG" if verbose else rtx_config.logging.level
        setup_logging(log_level, rtx_config.logging.file)
        
    except Exception as e:
        console.print(f"[red]Error loading configuration: {e}[/red]")
        if verbose:
            console.print_exception()
        sys.exit(1)


@main.command()
@click.pass_context
def connect(ctx):
    """Test connection to RTX830."""
    config: RTXConfig = ctx.obj['config']
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Connecting to RTX830...", total=None)
            
            with create_connection(config.rtx_connection.model_dump()) as conn:
                progress.update(task, description="Connected! Testing command execution...")
                hostname = conn.execute_command("show environment")
                
        console.print("[green]✓ Connection successful![/green]")
        console.print(f"RTX830 at {config.rtx_connection.host} is accessible")
        
    except RTXConnectionError as e:
        console.print(f"[red]✗ Connection failed: {e}[/red]")
        sys.exit(1)


@main.command()
@click.option(
    "--output", "-o",
    type=click.Path(path_type=Path),
    help="Output file path (default: stdout)"
)
@click.pass_context
def backup(ctx, output: Optional[Path]):
    """Create backup of current RTX830 configuration."""
    config: RTXConfig = ctx.obj['config']
    
    try:
        with create_connection(config.rtx_connection.model_dump()) as conn:
            config_mgr = ConfigManager(config)
            
            if output:
                # Save to specified file
                config_data = conn.get_running_config()
                output.parent.mkdir(parents=True, exist_ok=True)
                with open(output, 'w', encoding='utf-8') as f:
                    f.write(config_data)
                console.print(f"[green]✓ Configuration saved to: {output}[/green]")
            else:
                # Create timestamped backup
                backup_file = config_mgr.backup_config(conn)
                console.print(f"[green]✓ Backup created: {backup_file}[/green]")
            
    except Exception as e:
        console.print(f"[red]✗ Backup failed: {e}[/red]")
        sys.exit(1)


@main.command()
@click.argument("config_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--no-backup",
    is_flag=True,
    help="Skip creating backup before applying configuration"
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be applied without making changes"
)
@click.pass_context
def apply(ctx, config_file: Path, no_backup: bool, dry_run: bool):
    """Apply configuration file to RTX830."""
    config: RTXConfig = ctx.obj['config']
    
    try:
        config_mgr = ConfigManager(config)
        
        # Validate configuration file first
        validation = config_mgr.validate_config_file(config_file)
        
        if not validation['valid']:
            console.print("[red]✗ Configuration file validation failed:[/red]")
            for error in validation['errors']:
                console.print(f"  • {error}")
            sys.exit(1)
        
        if validation['warnings']:
            console.print("[yellow]⚠ Configuration file warnings:[/yellow]")
            for warning in validation['warnings']:
                console.print(f"  • {warning}")
        
        console.print(f"Found {validation['command_count']} configuration commands")
        
        if dry_run:
            # Show what would be applied
            with open(config_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            syntax = Syntax(content, "text", theme="monokai", line_numbers=True)
            console.print("\n[bold]Configuration to be applied:[/bold]")
            console.print(syntax)
            return
        
        # Confirm application
        if not click.confirm(f"Apply configuration from {config_file}?"):
            console.print("Operation cancelled")
            return
        
        with create_connection(config.rtx_connection.model_dump()) as conn:
            results = config_mgr.apply_config(
                conn, config_file, create_backup=not no_backup
            )
            
            if results['applied']:
                console.print("[green]✓ Configuration applied successfully![/green]")
                if results['backup_file']:
                    console.print(f"Backup created: {results['backup_file']}")
            else:
                console.print(f"[red]✗ Failed to apply configuration: {results['error']}[/red]")
                sys.exit(1)
            
    except Exception as e:
        console.print(f"[red]✗ Apply failed: {e}[/red]")
        sys.exit(1)


@main.command()
@click.argument("config_file", type=click.Path(exists=True, path_type=Path))
@click.pass_context
def diff(ctx, config_file: Path):
    """Show difference between current configuration and file."""
    config: RTXConfig = ctx.obj['config']
    
    try:
        with create_connection(config.rtx_connection.model_dump()) as conn:
            config_mgr = ConfigManager(config)
            diff_output = config_mgr.get_config_diff(conn, config_file)
            
            if diff_output.strip():
                syntax = Syntax(diff_output, "diff", theme="monokai")
                console.print(syntax)
            else:
                console.print("[green]No differences found[/green]")
            
    except Exception as e:
        console.print(f"[red]✗ Diff failed: {e}[/red]")
        sys.exit(1)


@main.command()
@click.argument("backup_file", type=click.Path(exists=True, path_type=Path))
@click.pass_context
def restore(ctx, backup_file: Path):
    """Restore configuration from backup file."""
    config: RTXConfig = ctx.obj['config']
    
    if not click.confirm(f"Restore configuration from {backup_file}?"):
        console.print("Operation cancelled")
        return
    
    try:
        with create_connection(config.rtx_connection.model_dump()) as conn:
            config_mgr = ConfigManager(config)
            
            if config_mgr.restore_from_backup(conn, backup_file):
                console.print("[green]✓ Configuration restored successfully![/green]")
            else:
                console.print("[red]✗ Failed to restore configuration[/red]")
                sys.exit(1)
            
    except Exception as e:
        console.print(f"[red]✗ Restore failed: {e}[/red]")
        sys.exit(1)


@main.command()
@click.option(
    "--cleanup",
    is_flag=True,
    help="Remove old backup files based on retention policy"
)
@click.pass_context
def backups(ctx, cleanup: bool):
    """List backup files."""
    config: RTXConfig = ctx.obj['config']
    config_mgr = ConfigManager(config)
    
    if cleanup:
        removed_count = config_mgr.cleanup_old_backups()
        console.print(f"[green]Removed {removed_count} old backup files[/green]")
        return
    
    backup_list = config_mgr.list_backups()
    
    if not backup_list:
        console.print("No backup files found")
        return
    
    table = Table(title="RTX830 Configuration Backups")
    table.add_column("File", style="cyan")
    table.add_column("Size", justify="right")
    table.add_column("Modified", style="green")
    table.add_column("Age (days)", justify="right")
    
    for backup in backup_list:
        size_bytes = backup['size']
        table.add_row(
            backup['name'],
            f"{size_bytes} B",
            backup['modified'].strftime("%Y-%m-%d %H:%M:%S"),
            str(backup['age_days'])
        )
    
    console.print(table)


@main.command()
@click.argument("output_file", type=click.Path(path_type=Path))
def init_config(output_file: Path):
    """Create example configuration file."""
    try:
        # Create config manager without loading existing config
        config_manager = ConfigFileManager()
        config_manager.create_example_config(str(output_file))
        
        console.print(f"[green]✓ Example configuration created: {output_file}[/green]")
        console.print("\nPlease edit the configuration file with your RTX830 details:")
        console.print(f"  • Host IP address")
        console.print(f"  • SSH username")  
        console.print(f"  • SSH private key file path")
        
    except Exception as e:
        console.print(f"[red]✗ Failed to create configuration: {e}[/red]")
        sys.exit(1)


@main.command()
@click.argument("config_file", type=click.Path(exists=True, path_type=Path))
@click.pass_context
def validate(ctx, config_file: Path):
    """Validate configuration file syntax."""
    config: RTXConfig = ctx.obj['config']
    config_mgr = ConfigManager(config)
    
    validation = config_mgr.validate_config_file(config_file)
    
    if validation['valid']:
        console.print(f"[green]✓ Configuration file is valid[/green]")
        console.print(f"Found {validation['command_count']} commands")
    else:
        console.print(f"[red]✗ Configuration file is invalid[/red]")
        for error in validation['errors']:
            console.print(f"  • {error}")
    
    if validation['warnings']:
        console.print(f"[yellow]⚠ Warnings:[/yellow]")
        for warning in validation['warnings']:
            console.print(f"  • {warning}")


@main.command()
@click.option(
    "--format", "-f",
    type=click.Choice(['table', 'json', 'text']),
    default='table',
    help="Output format"
)
@click.pass_context
def status(ctx, format: str):
    """Show RTX830 status information."""
    config: RTXConfig = ctx.obj['config']

    try:
        with create_connection(config.rtx_connection.model_dump()) as conn:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Gathering status information...", total=None)
                status_info = conn.get_status_info()
            
            logging.info(status_info)
            if format == 'json':
                import json
                console.print(json.dumps(status_info, indent=2, ensure_ascii=False))
            else:  # text format (default)
                for key, value in status_info.items():
                    console.print(f"\n[bold cyan]{key.upper()}:[/bold cyan]")
                    console.print(value)

    except RTXConnectionError as e:
        console.print(f"[red]✗ Failed to get status: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()