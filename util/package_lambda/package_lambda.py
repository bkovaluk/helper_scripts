#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script: package_lambda.py
Description: A modernized script to package a Python Lambda function with dependencies, using Docker for isolation
             or directly installing dependencies if Docker is unavailable.

Usage:
    python package_lambda.py <base_dir> [--log-level LOG_LEVEL] [--use-docker]

Arguments:
    base_dir: The root directory of the Lambda function.

Options:
    --log-level LOG_LEVEL: Set logging level (default: INFO).
    --use-docker: Use Docker to package dependencies in a Lambda-compatible environment (default: False).
    --python-version: Specify the Python version for Lambda runtime compatibility (default: 3.8).
    --requirements-file: Specify an alternative requirements file (default: requirements.txt).

Requirements:
    - Docker (optional)
    - Rich
    - Typer
"""

__author__ = "Bradley Kovaluk"
__version__ = "2.0"
__date__ = "2024-10-28"


import shutil
from pathlib import Path
import typer
from rich.logging import RichHandler
from rich.console import Console
import logging
import subprocess
from typing import Optional

# Top-level configuration
EXCLUDED_PACKAGES = {'boto3', 'botocore'}
PACKAGE_DIR_NAME = 'package'
RELEASE_DIR_NAME = 'release'
DEFAULT_PYTHON_VERSION = '3.11'
DEFAULT_REQUIREMENTS_FILE = 'requirements.txt'

# Configure Rich console and logger
console = Console()
logging.basicConfig(level=logging.INFO, format="%(message)s", handlers=[RichHandler(rich_tracebacks=True)])
logger = logging.getLogger("lambda-packager")

# Initialize Typer app
app = typer.Typer(help="Package a Python Lambda function into a zip file for AWS deployment.")

def install_dependencies(base_dir: Path, use_docker: bool, python_version: str, requirements_file: str):
    """Install dependencies either directly or in Docker, depending on the flag."""
    requirements_path = base_dir / requirements_file
    if not requirements_path.exists():
        console.print("[yellow]Requirements file not found; skipping dependency installation.[/yellow]")
        return

    package_dir = base_dir / PACKAGE_DIR_NAME
    package_dir.mkdir(exist_ok=True)

    if use_docker:
        # Use Docker to install dependencies in a Lambda-compatible environment
        console.print(f"[blue]Using Docker to package dependencies with Python {python_version}...[/blue]")
        docker_image = f"public.ecr.aws/lambda/python:{python_version}"
        docker_command = [
            "docker", "run", "--rm", "-v", f"{base_dir}:/var/task",
            docker_image,
            "pip", "install", "-r", f"/var/task/{requirements_file}", "-t", f"/var/task/{PACKAGE_DIR_NAME}"
        ]
        subprocess.run(docker_command, check=True)
    else:
        # Local installation of dependencies
        console.print(f"[blue]Installing dependencies locally for Python {python_version}...[/blue]")
        subprocess.run([
            "pip", "install", "-r", str(requirements_path), "-t", str(package_dir)
        ], check=True)

def package_lambda(base_dir: Path):
    """Package Lambda function with dependencies."""
    release_dir = base_dir / RELEASE_DIR_NAME
    package_dir = base_dir / PACKAGE_DIR_NAME

    # Clear the release directory if it exists
    if release_dir.exists():
        shutil.rmtree(release_dir)
    release_dir.mkdir(parents=True, exist_ok=True)

    # Copy dependencies from the package directory, skipping excluded packages
    for item in package_dir.iterdir():
        if item.is_dir() and item.name not in EXCLUDED_PACKAGES:
            shutil.copytree(item, release_dir / item.name, dirs_exist_ok=True)
        elif item.is_file() and item.name.split('-')[0] not in EXCLUDED_PACKAGES:
            shutil.copy2(item, release_dir / item.name)

    # Copy the Lambda function code
    for item in base_dir.iterdir():
        if item.is_dir() and item.name not in {PACKAGE_DIR_NAME, RELEASE_DIR_NAME, 'tests'}:
            shutil.copytree(item, release_dir / item.name, dirs_exist_ok=True)
        elif item.is_file():
            shutil.copy2(item, release_dir / item.name)

    # Zip the release directory for deployment
    zip_path = shutil.make_archive(str(base_dir / base_dir.name), 'zip', root_dir=release_dir)
    console.print(f"[green]Packaged Lambda function to {zip_path}[/green]")

    # Clean up the package directory after zipping
    if package_dir.exists():
        shutil.rmtree(package_dir)

@app.command()
def main(
    base_dir: Path = typer.Argument(..., help="The base directory path of the Lambda function."),
    log_level: Optional[str] = typer.Option('INFO', "--log-level", help="Set logging level (default: INFO)"),
    use_docker: bool = typer.Option(False, "--use-docker", help="Use Docker to package dependencies (default: False)"),
    python_version: str = typer.Option(DEFAULT_PYTHON_VERSION, "--python-version", help="Python version for Lambda runtime compatibility (default: 3.8)"),
    requirements_file: str = typer.Option(DEFAULT_REQUIREMENTS_FILE, "--requirements-file", help="Path to the requirements file (default: requirements.txt)")
):
    """Main function for packaging Lambda function."""
    logger.setLevel(log_level.upper())
    logger.info("Starting Lambda packaging script...")

    try:
        install_dependencies(base_dir, use_docker, python_version, requirements_file)
        package_lambda(base_dir)
        logger.info("Packaging completed successfully.")
    except Exception as e:
        console.print(f"[red]An error occurred: {str(e)}[/red]")
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()
