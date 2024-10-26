#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script: get_lambda_cold_storage.py
Description: This script retrieves AWS Lambda function versions in "cold storage" (inactive versions based on last modification date).

Usage:
    python get_lambda_cold_storage.py [--days-old DAYS] [--profile PROFILE] [--region REGION] [--verbose]

Options:
    --days-old DAYS     Number of days since last modification to consider a version in cold storage (default: 30).
    --profile PROFILE   The name of the AWS profile to use (default: default).
    --region REGION     The AWS region name (default: us-east-1).
    --verbose           Enable verbose output to see iteration through Lambda functions.

Requirements:
    - boto3
    - typer
    - rich
"""

__author__ = "Bradley Kovaluk"
__version__ = "1.2"
__date__ = "2024-10-26"

import boto3
import typer
import logging
from datetime import datetime, timedelta, timezone
from rich import print
from rich.logging import RichHandler
from rich.console import Console
from rich.table import Table
from typing import Dict, List

# Configure Rich logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True)]
)
logger = logging.getLogger(__name__)
console = Console()

app = typer.Typer(help="Retrieve AWS Lambda function versions in cold storage.")

def get_lambda_versions_in_cold_storage(
    lambda_client,
    days_old: int = 30,
    verbose: bool = False
) -> Dict[str, Dict[str, int]]:
    """
    Retrieves Lambda function versions in cold storage based on inactivity threshold.
    
    Args:
        lambda_client: The AWS Lambda client.
        days_old (int): Number of days to consider a version inactive (default: 30).
        verbose (bool): If True, enables verbose output to track iteration.
        
    Returns:
        dict: Dictionary with function name as key and count of inactive versions and total size as values.
    """
    cold_storage_versions = {}
    threshold_date = datetime.now(timezone.utc) - timedelta(days=days_old)

    paginator = lambda_client.get_paginator("list_functions")
    function_pages = paginator.paginate()

    for page in function_pages:
        for function in page["Functions"]:
            function_name = function["FunctionName"]
            if verbose:
                logger.info(f"Checking function: {function_name}")

            version_paginator = lambda_client.get_paginator("list_versions_by_function")
            version_pages = version_paginator.paginate(FunctionName=function_name)

            version_count = 0
            total_size = 0

            for version_page in version_pages:
                for version in version_page["Versions"]:
                    if version["Version"] == "$LATEST":
                        continue

                    last_modified = datetime.strptime(version["LastModified"], '%Y-%m-%dT%H:%M:%S.%f%z')
                    if last_modified < threshold_date:
                        version_count += 1
                        total_size += version["CodeSize"]
                        
                        if verbose:
                            logger.info(f"  - Cold storage version: {version['Version']} (Size: {version['CodeSize']} bytes)")

            if version_count > 0:
                cold_storage_versions[function_name] = {
                    "VersionCount": version_count,
                    "TotalSize": total_size
                }

    return cold_storage_versions

@app.command()
def main(
    days_old: int = typer.Option(30, "--days-old", help="Number of days since last modification to consider a version in cold storage."),
    profile: str = typer.Option("default", "--profile", help="The name of the AWS profile to use."),
    region: str = typer.Option("us-east-1", "--region", help="The AWS region name."),
    verbose: bool = typer.Option(False, "--verbose", help="Enable verbose output to see iteration through Lambda functions.")
):
    """
    Retrieve AWS Lambda function versions in cold storage based on inactivity threshold.
    """
    try:
        session = boto3.Session(profile_name=profile, region_name=region)
        lambda_client = session.client("lambda")

        cold_storage_versions = get_lambda_versions_in_cold_storage(
            lambda_client=lambda_client,
            days_old=days_old,
            verbose=verbose
        )

        if not cold_storage_versions:
            console.print("[bold green]No Lambda versions found in cold storage.[/bold green]")
        else:
            # Prepare table output
            table = Table(title="Lambda Functions in Cold Storage")
            table.add_column("Function Name", style="bold cyan")
            table.add_column("Cold Versions", style="magenta", justify="right")
            table.add_column("Total Size (bytes)", style="green", justify="right")

            total_storage_size = 0
            for function_name, data in cold_storage_versions.items():
                table.add_row(
                    function_name,
                    str(data["VersionCount"]),
                    str(data["TotalSize"])
                )
                total_storage_size += data["TotalSize"]

            console.print(table)
            console.print(f"\n[bold yellow]Total Cold Storage Size:[/bold yellow] {total_storage_size} bytes")
    except Exception as e:
        logger.error(f"[bold red]Error:[/bold red] {str(e)}")
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()
