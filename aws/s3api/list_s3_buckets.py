#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script: list_s3_buckets.py
Description: This script lists all S3 buckets in your AWS account. If a substring is provided, only buckets containing
             the substring in their names are listed.

Usage:
    python list_s3_buckets.py [--substring SUBSTRING] [--profile PROFILE] [--region REGION]

Options:
    --substring SUBSTRING The substring to filter bucket names (default: None).
    --profile PROFILE     The name of the AWS profile to use (default: default).
    --region REGION       The AWS region name (default: us-east-1).

Requirements:
    - boto3
    - typer
    - logging
"""

__author__ = "Bradley Kovaluk"
__version__ = "1.1"
__date__ = "2024-07-01"

import boto3
import logging
import typer
from typing import Optional

# Set up logging
logging.basicConfig(
    level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = typer.Typer(
    help="List all S3 buckets in your AWS account, optionally filtering by a substring."
)

def list_s3_buckets(
    profile_name: str,
    region_name: str = 'us-east-1',
    substring: Optional[str] = None
):
    """List all S3 buckets in the AWS account, optionally filtering by a substring."""
    session = boto3.Session(profile_name=profile_name, region_name=region_name)
    s3_client = session.client('s3')

    try:
        response = s3_client.list_buckets()
        buckets = response.get('Buckets', [])
    except Exception as e:
        logger.error(f"Error listing buckets: {str(e)}")
        return

    if substring:
        buckets = [bucket for bucket in buckets if substring in bucket['Name']]

    if buckets:
        logger.info("S3 Buckets:")
        for bucket in buckets:
            logger.info(f" - {bucket['Name']}")
    else:
        logger.info("No buckets found.")

@app.command()
def main(
    substring: Optional[str] = typer.Option(
        None, "--substring", help="The substring to filter bucket names."
    ),
    profile: str = typer.Option(
        "default", "--profile", help="The name of the AWS profile to use (default: default)."
    ),
    region: str = typer.Option(
        "us-east-1", "--region", help="The AWS region name (default: us-east-1)."
    )
):
    """List all S3 buckets in your AWS account, optionally filtering by a substring."""
    list_s3_buckets(
        profile_name=profile,
        region_name=region,
        substring=substring
    )

if __name__ == "__main__":
    app()
