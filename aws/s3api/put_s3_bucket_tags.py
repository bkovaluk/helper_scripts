#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script: put_s3_bucket_tags.py
Description: Sets multiple tags on an S3 bucket, replacing all existing tags.

Usage:
    python put_s3_bucket_tags.py <bucket_name> <tag1=val1> <tag2=val2> ... [--profile PROFILE] [--region REGION]

Arguments:
    bucket_name  The name of the S3 bucket.
    tag1=val1    Tag in "Key=Value" format (e.g., Environment=Production).

Options:
    --profile PROFILE  The name of the AWS profile to use (default: default).
    --region REGION    The AWS region name (default: us-east-1).
"""

__author__ = "Bradley Kovaluk"
__version__ = "1.1"
__date__ = "2024-10-31"

import boto3
import typer
from rich.console import Console
from rich.logging import RichHandler
import logging

console = Console(force_terminal=True)
logging.basicConfig(
    level="INFO",
    format="%(message)s",
    handlers=[RichHandler(console=console, markup=True, rich_tracebacks=True)]
)
logger = logging.getLogger(__name__)

app = typer.Typer(help="Set multiple tags on an S3 bucket, replacing all existing tags.")

def put_s3_bucket_tags(
    bucket_name: str,
    tags: dict,
    profile_name: str = "default",
    region_name: str = "us-east-1"
):
    session = boto3.Session(profile_name=profile_name, region_name=region_name)
    s3_client = session.client('s3')

    # Convert dictionary to the required format
    tag_set = [{'Key': key, 'Value': value} for key, value in tags.items()]

    try:
        s3_client.put_bucket_tagging(
            Bucket=bucket_name,
            Tagging={'TagSet': tag_set}
        )
        logger.info(f"[green]Successfully[/green] set multiple tags on bucket '[bold]{bucket_name}[/bold]'.")
    except Exception as e:
        logger.error(f"[red]Error[/red] setting tags on bucket '{bucket_name}': {str(e)}")
        raise typer.Exit(code=1)

@app.command()
def main(
    bucket_name: str = typer.Argument(..., help="The name of the S3 bucket"),
    tags: list[str] = typer.Argument(..., help="Tags in 'Key=Value' format, e.g., Environment=Production"),
    profile: str = typer.Option("default", "--profile", help="The name of the AWS profile to use (default: default)"),
    region: str = typer.Option("us-east-1", "--region", help="The AWS region name (default: us-east-1)")
):
    # Convert tags list to dictionary
    tag_dict = {}
    for tag in tags:
        if "=" not in tag:
            logger.error(f"Invalid tag format '{tag}'. Expected format is 'Key=Value'.")
            raise typer.Exit(code=1)
        
        key, value = tag.split("=", 1)
        tag_dict[key] = value

    put_s3_bucket_tags(bucket_name, tag_dict, profile_name=profile, region_name=region)

if __name__ == "__main__":
    app()
