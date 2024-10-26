#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script: get_lambda_cold_storage.py
Description: This script retrieves AWS Lambda function versions in "cold storage" (inactive versions based on last modification date).

Usage:
    python get_lambda_cold_storage.py [--days-old DAYS] [--profile PROFILE] [--region REGION]

Options:
    --days-old DAYS     Number of days since last modification to consider a version in cold storage (default: 30).
    --profile PROFILE   The name of the AWS profile to use (default: default).
    --region REGION     The AWS region name (default: us-east-1).

Requirements:
    - boto3
    - typer
    - rich
"""

__author__ = "Bradley Kovaluk"
__version__ = "1.0"
__date__ = "2024-10-25"

import boto3
import typer
import logging
from datetime import datetime, timedelta, timezone
from rich import print
from rich.logging import RichHandler
from rich.console import Console
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
    iam_client,
    days_old: int = 30
) -> Dict[str, List[str]]:
    """
    Retrieves Lambda function versions in cold storage based on inactivity threshold.
    
    Args:
        iam_client: The AWS Lambda client.
        days_old (int): Number of days to consider a version inactive (default: 30).
        
    Returns:
        dict: Dictionary with function name as key and list of inactive versions as value.
    """
    cold_storage_versions = {}
    threshold_date = datetime.now(timezone.utc) - timedelta(days=days_old)

    functions = iam_client.list_functions()["Functions"]
    for function in functions:
        function_name = function["FunctionName"]
        versions = iam_client.list_versions_by_function(FunctionName=function_name)["Versions"]
        
        for version in versions:
            if version["Version"] == "$LATEST":
                continue

            last_modified = datetime.strptime(version["LastModified"], '%Y-%m-%dT%H:%M:%S.%f%z')
            if last_modified < threshold_date:
                if function_name not in cold_storage_versions:
                    cold_storage_versions[function_name] = []
                cold_storage_versions[function_name].append(version["Version"])

    return cold_storage_versions

@app.command()
def main(
    days_old: int = typer.Option(30, "--days-old", help="Number of days since last modification to consider a version in cold storage."),
    profile: str = typer.Option("default", "--profile", help="The name of the AWS profile to use."),
    region: str = typer.Option("us-east-1", "--region", help="The AWS region name."),
):
    """
    Retrieve AWS Lambda function versions in cold storage based on inactivity threshold.
    """
    try:
        session = boto3.Session(profile_name=profile, region_name=region)
        lambda_client = session.client("lambda")

        cold_storage_versions = get_lambda_versions_in_cold_storage(lambda_client, days_old)

        if not cold_storage_versions:
            console.print("[bold green]No Lambda versions found in cold storage.[/bold green]")
        else:
            console.print("[bold cyan]Lambda versions in cold storage:[/bold cyan]")
            for function_name, versions in cold_storage_versions.items():
                console.print(f"[bold]{function_name}:[/bold] {', '.join(versions)}")
    except Exception as e:
        logger.error(f"[bold red]Error:[/bold red] {str(e)}")
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()