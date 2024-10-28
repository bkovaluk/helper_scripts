#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script: run_script.py
Description: A script to create a virtual environment, install dependencies from a requirements file, 
             and execute a specified Python script within that environment.

Usage:
    python run_script.py <base_dir> <script_file_path>

Arguments:
    base_dir: The base directory path where the virtual environment will be created.
    script_file_path: The Python script to be executed within the virtual environment.

Requirements:
    - Python 3.3+ (includes venv)
    - Typer
    - Rich

Author: Your Name
Version: 2.0
Date: 2024-01-01
"""

from pathlib import Path
from subprocess import check_call, CalledProcessError
import typer
from rich.logging import RichHandler
from rich.console import Console
import logging
import platform
import sys

# Configure Rich logger
logging.basicConfig(level=logging.INFO, format="%(message)s", handlers=[RichHandler()])
logger = logging.getLogger("venv-runner")
console = Console()

app = typer.Typer(help="Create a virtual environment, install dependencies, and run a Python script within the venv.")

def create_venv(base_dir: Path):
    """Create a virtual environment if it doesn't already exist."""
    venv_path = base_dir / 'venv'
    if not venv_path.exists():
        try:
            check_call([sys.executable, '-m', 'venv', str(venv_path)])
            logger.info("Virtual environment created.")
        except CalledProcessError:
            console.print("[red]Failed to create virtual environment.[/red]")
            raise typer.Exit(code=1)

def get_python_executable(base_dir: Path) -> Path:
    """Get the path to the Python executable within the virtual environment."""
    if platform.system() == 'Windows':
        return base_dir / 'venv' / 'Scripts' / 'python.exe'
    return base_dir / 'venv' / 'bin' / 'python'

def upgrade_pip(base_dir: Path):
    """Upgrade pip within the virtual environment."""
    venv_python = get_python_executable(base_dir)
    try:
        check_call([str(venv_python), '-m', 'pip', 'install', '--upgrade', 'pip'])
        logger.info("pip upgraded.")
    except CalledProcessError:
        console.print("[red]Failed to upgrade pip.[/red]")
        raise typer.Exit(code=1)

def install_requirements(base_dir: Path):
    """Install requirements from the requirements.txt file within the virtual environment."""
    venv_python = get_python_executable(base_dir)
    requirements_path = base_dir / 'requirements.txt'
    if requirements_path.exists():
        try:
            check_call([str(venv_python), '-m', 'pip', 'install', '-r', str(requirements_path)])
            logger.info("Requirements installed.")
        except CalledProcessError:
            console.print("[red]Failed to install requirements.[/red]")
            raise typer.Exit(code=1)
    else:
        logger.warning("requirements.txt not found. Skipping dependency installation.")

def run_python_script(base_dir: Path, script_file: Path):
    """Run the specified Python script within the virtual environment."""
    venv_python = get_python_executable(base_dir)
    try:
        check_call([str(venv_python), str(script_file)])
        logger.info("Python script executed.")
    except CalledProcessError:
        console.print(f"[red]Failed to execute script: {script_file}[/red]")
        raise typer.Exit(code=1)

@app.command()
def main(
    base_dir: Path = typer.Argument(..., help="The base directory path for the Lambda function"),
    script_file: Path = typer.Argument(..., help="The path to the Python script file to run")
):
    """Create a virtual environment, install dependencies, and run a Python script within the venv."""
    logger.info("Starting script.")

    # Create virtual environment
    create_venv(base_dir)

    # Upgrade pip
    upgrade_pip(base_dir)

    # Install requirements
    install_requirements(base_dir)

    # Run Python script
    run_python_script(base_dir, script_file)

    logger.info("Script execution completed.")

if __name__ == "__main__":
    app()
