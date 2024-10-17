#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script: add_s3_lifecycle_policy.py
Description: This script adds a lifecycle policy to an S3 bucket using the S3 API.

Usage:
    python add_s3_lifecycle_policy.py <bucket_name> <lifecycle_policy_path> [--profile PROFILE] [--region REGION]

Arguments:
    bucket_name            The name of the S3 bucket.
    lifecycle_policy_path  The path to the lifecycle policy JSON file.

Options:
    --profile PROFILE      The name of the AWS profile to use (default: default).
    --region REGION        The AWS region name (default: us-east-1).

Requirements:
    - boto3
    - typer
    - logging
"""

__author__ = "Bradley Kovaluk"
__version__ = "1.1"
__date__ = "2024-07-02"

import boto3
import logging
import json
import typer
from typing import Optional

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = typer.Typer(help="Add a lifecycle policy to an S3 bucket using the S3 API.")

def add_s3_lifecycle_policy(
    bucket_name: str,
    lifecycle_policy_path: str,
    profile_name: str = "default",
    region_name: str = "us-east-1"
):
    """Add a lifecycle policy to an S3 bucket."""
    session = boto3.Session(profile_name=profile_name, region_name=region_name)
    s3_client = session.client('s3')

    # Read lifecycle policy from the specified file
    try:
        with open(lifecycle_policy_path, 'r') as policy_file:
            lifecycle_policy = json.load(policy_file)
    except Exception as e:
        logger.error(f"Error reading lifecycle policy file '{lifecycle_policy_path}': {str(e)}")
        raise typer.Exit(code=1)

    try:
        # Put lifecycle policy on the bucket
        s3_client.put_bucket_lifecycle_configuration(
            Bucket=bucket_name,
            LifecycleConfiguration=lifecycle_policy
        )
        logger.info(f"Applied lifecycle policy from {lifecycle_policy_path} to bucket: {bucket_name}")
    except Exception as e:
        logger.error(f"Error applying lifecycle policy to bucket '{bucket_name}': {str(e)}")
        raise typer.Exit(code=1)

@app.command()
def main(
    bucket_name: str = typer.Argument(..., help="The name of the S3 bucket"),
    lifecycle_policy_path: str = typer.Argument(..., help="The path to the lifecycle policy JSON file"),
    profile: str = typer.Option("default", "--profile", help="The name of the AWS profile to use (default: default)"),
    region: str = typer.Option("us-east-1", "--region", help="The AWS region name (default: us-east-1)")
):
    """Add a lifecycle policy to an S3 bucket."""
    add_s3_lifecycle_policy(
        bucket_name=bucket_name,
        lifecycle_policy_path=lifecycle_policy_path,
        profile_name=profile,
        region_name=region
    )

if __name__ == "__main__":
    app()
