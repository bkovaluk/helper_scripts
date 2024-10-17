#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script: copy_s3_objects.py
Description: This script copies objects from a source S3 bucket (optionally from a specified prefix)
             to a destination S3 bucket, potentially in another AWS account and/or region.
             It handles large files using multipart upload.

Usage:
    python copy_s3_objects.py --source-bucket SOURCE_BUCKET [--source-prefix SOURCE_PREFIX]
                              --destination-bucket DESTINATION_BUCKET [--destination-prefix DESTINATION_PREFIX]
                              [--source-region SOURCE_REGION] [--destination-region DESTINATION_REGION]
                              [--profile PROFILE] [--include INCLUDE_PATTERN] [--exclude EXCLUDE_PATTERN]

Requirements:
    - boto3
    - botocore
    - logging
    - typer
"""

__author__ = "Bradley Kovaluk"
__version__ = "1.0"
__date__ = "2023-10-14"

import boto3
import logging
import os
from botocore.exceptions import ClientError
from boto3.s3.transfer import TransferConfig
from fnmatch import fnmatch
import typer
from typing import Optional

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = typer.Typer(help="Copy objects from a source S3 bucket to a destination S3 bucket, handling large files with multipart upload, including cross-region support.")

def copy_object(s3_client_source, s3_client_destination, source_bucket, source_key, destination_bucket, destination_key, config):
    try:
        copy_source = {
            'Bucket': source_bucket,
            'Key': source_key
        }
        
        s3_client_destination.copy(
            CopySource=copy_source,
            Bucket=destination_bucket,
            Key=destination_key,
            Config=config,
            SourceClient=s3_client_source
        )
        logger.info(f"Copied {source_bucket}/{source_key} to {destination_bucket}/{destination_key}")
    except ClientError as e:
        logger.error(f"Error copying {source_bucket}/{source_key} to {destination_bucket}/{destination_key}: {e}")

def should_include_object(key, include_pattern, exclude_pattern):
    if exclude_pattern and fnmatch(key, exclude_pattern):
        return False
    if include_pattern and not fnmatch(key, include_pattern):
        return False
    return True

@app.command()
def main(
    source_bucket: str = typer.Option(..., '--source-bucket', help="The name of the source S3 bucket."),
    source_prefix: str = typer.Option('', '--source-prefix', help="(Optional) The prefix (folder) in the source bucket to copy from."),
    destination_bucket: str = typer.Option(..., '--destination-bucket', help="The name of the destination S3 bucket."),
    destination_prefix: str = typer.Option('', '--destination-prefix', help="(Optional) The prefix (folder) in the destination bucket to copy to."),
    source_region: str = typer.Option('us-east-1', '--source-region', help="The AWS region of the source bucket (default: us-east-1)."),
    destination_region: str = typer.Option('us-east-1', '--destination-region', help="The AWS region of the destination bucket (default: us-east-1)."),
    profile: str = typer.Option('default', '--profile', help="The AWS profile to use (default: default)."),
    include: Optional[str] = typer.Option(None, '--include', help="(Optional) Only include objects that match this pattern (e.g., '*.txt')."),
    exclude: Optional[str] = typer.Option(None, '--exclude', help="(Optional) Exclude objects that match this pattern."),
):
    """Copy objects from a source S3 bucket to a destination S3 bucket, handling large files with multipart upload, including cross-region support."""
    
    session = boto3.Session(profile_name=profile)

    # Create S3 clients for source and destination regions
    s3_client_source = session.client('s3', region_name=source_region)
    s3_client_destination = session.client('s3', region_name=destination_region)

    # Configure TransferConfig for multipart uploads
    config = TransferConfig(
        multipart_threshold=1024 * 25,  # 25 MB
        max_concurrency=10,
        multipart_chunksize=1024 * 25,  # 25 MB
        use_threads=True
    )

    # Paginator for listing objects in the source bucket
    paginator = s3_client_source.get_paginator('list_objects_v2')
    operation_parameters = {'Bucket': source_bucket, 'Prefix': source_prefix}

    for page in paginator.paginate(**operation_parameters):
        if 'Contents' in page:
            for obj in page['Contents']:
                source_key = obj['Key']
                if not should_include_object(source_key, include, exclude):
                    continue
                # Construct destination key
                relative_key = os.path.relpath(source_key, start=source_prefix) if source_prefix else source_key
                destination_key = os.path.join(destination_prefix, relative_key).replace('\\', '/')
                # Copy the object
                copy_object(s3_client_source, s3_client_destination, source_bucket, source_key, destination_bucket, destination_key, config)
        else:
            logger.info("No objects found in the source bucket with the specified prefix.")
            break

if __name__ == "__main__":
    app()
