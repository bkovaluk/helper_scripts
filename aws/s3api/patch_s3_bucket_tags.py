#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script: patch_s3_bucket_tags.py
Description: Adds or updates multiple tags on an S3 bucket while preserving existing tags.

Usage:
    python patch_s3_bucket_tags.py <bucket_name> <tag1=val1> <tag2=val2> ... [--profile PROFILE] [--region REGION]

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

app = typer.Typer(help="Add or update multiple tags on an S3 bucket, preserving existing tags.")

def patch_s3_bucket_tags(
    bucket_name: str,
    tags: dict,
    profile_name: str = "default",
    region_name: str = "us-east-1"
):
    session = boto3.Session(profile_name=profile_name, region_name=region_name)
    s3_client = session.client('s3')

    # Retrieve current tags
    try:
        current_tags = s3_client.get_bucket_tagging(Bucket=bucket_name)['TagSet']
    except s3_client.exceptions.ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchTagSet':
            current_tags = []  # No tags currently set
        else:
            logger.error(f"[red]Error[/red] retrieving tags for bucket '{bucket_name}': {str(e)}")
            raise typer.Exit(code=1)

    # Convert current tags to a dictionary for easy updating
    current_tags_dict = {tag['Key']: tag['Value'] for tag in current_tags}

    # Update or add new tags
    current_tags_dict.update(tags)

    # Convert back to the required format
    updated_tags = [{'Key': key, 'Value': value} for key, value in current_tags_dict.items()]

    # Apply updated tag set back to the bucket
    try:
        s3_client.put_bucket_tagging(
            Bucket=bucket_name,
            Tagging={'TagSet': updated_tags}
        )
        logger.info(f"[green]Successfully[/green] patched multiple tags on bucket '[bold]{bucket_name}[/bold]'.")
    except Exception as e:
        logger.error(f"[red]Error[/red] updating tags on bucket '{bucket_name}': {str(e)}")
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

    patch_s3_bucket_tags(bucket_name, tag_dict, profile_name=profile, region_name=region)

if __name__ == "__main__":
    app()
