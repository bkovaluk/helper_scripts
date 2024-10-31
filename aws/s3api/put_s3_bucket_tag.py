#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script: put_s3_bucket_tag.py
Description: This script sets a tag on an S3 bucket using the S3 API. It replaces any existing tags with the specified one.

Usage:
    python put_s3_bucket_tag.py <bucket_name> <tag_name> <tag_value> [--profile PROFILE] [--region REGION]

Arguments:
    bucket_name  The name of the S3 bucket.
    tag_name     The name of the tag to set.
    tag_value    The value for the specified tag.

Options:
    --profile PROFILE  The name of the AWS profile to use (default: default).
    --region REGION    The AWS region name (default: us-east-1).

Requirements:
    - boto3
    - typer
    - rich
"""

__author__ = "Bradley Kovaluk"
__version__ = "1.1"
__date__ = "2024-10-31"

import boto3
import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.traceback import install
from typing import Optional
import logging

# Set up rich logging and console
install()
console = Console()
logging.basicConfig(level="INFO", format="%(message)s", handlers=[RichHandler()])
logger = logging.getLogger(__name__)

app = typer.Typer(help="Add or update a tag on an S3 bucket using the S3 API.")

def update_s3_bucket_tag(
    bucket_name: str,
    tag_name: str,
    tag_value: str,
    profile_name: str = "default",
    region_name: str = "us-east-1"
):
    """Add or update a tag on an S3 bucket."""
    session = boto3.Session(profile_name=profile_name, region_name=region_name)
    s3_client = session.client('s3')

    # Set the specified tag directly
    tags = [{'Key': tag_name, 'Value': tag_value}]

    try:
        # Apply tags to the bucket
        s3_client.put_bucket_tagging(
            Bucket=bucket_name,
            Tagging={'TagSet': tags}
        )
        logger.info(f"[green]Successfully[/green] set tag '[bold]{tag_name}[/bold]' with value '[bold]{tag_value}[/bold]' on bucket: '[bold]{bucket_name}[/bold]'.")
    except Exception as e:
        logger.error(f"[red]Error[/red] updating tag on bucket '[bold]{bucket_name}[/bold]': {str(e)}")
        raise typer.Exit(code=1)

@app.command()
def main(
    bucket_name: str = typer.Argument(..., help="The name of the S3 bucket"),
    tag_name: str = typer.Argument(..., help="The name of the tag to add or update"),
    tag_value: str = typer.Argument(..., help="The value for the specified tag"),
    profile: str = typer.Option("default", "--profile", help="The name of the AWS profile to use (default: default)"),
    region: str = typer.Option("us-east-1", "--region", help="The AWS region name (default: us-east-1)")
):
    """Add or update a tag on an S3 bucket."""
    console.print(f"[cyan]Starting tag update for bucket:[/cyan] [bold]{bucket_name}[/bold]", style="cyan")
    update_s3_bucket_tag(
        bucket_name=bucket_name,
        tag_name=tag_name,
        tag_value=tag_value,
        profile_name=profile,
        region_name=region
    )

if __name__ == "__main__":
    app()
