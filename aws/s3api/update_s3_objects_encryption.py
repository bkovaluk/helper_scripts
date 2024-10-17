#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script: update_s3_objects_encryption.py
Description: This script modifies objects in an S3 bucket within a specified prefix to use new encryption settings (KMS or SSE-S3).

Usage:
    python update_s3_objects_encryption.py <bucket_name> [--kms-key-id KMS_KEY_ID] [--sse-s3] [--prefix PREFIX] [--profile PROFILE] [--region REGION]

Arguments:
    bucket_name       The name of the S3 bucket.

Options:
    --kms-key-id KMS_KEY_ID    The KMS key ID to use for encryption.
    --sse-s3                   Use SSE-S3 for encryption.
    --prefix PREFIX            The prefix of the objects to modify (default: '').
    --profile PROFILE          The name of the AWS profile to use (default: default).
    --region REGION            The AWS region name (default: us-east-1).

Requirements:
    - boto3
    - typer
    - logging
"""

__author__ = "Bradley Kovaluk"
__version__ = "1.1"
__date__ = "2024-07-26"

import boto3
import logging
from botocore.exceptions import ClientError
import typer
from typing import Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = typer.Typer(help="Modify S3 objects to use new encryption settings (KMS or SSE-S3).")

def get_s3_client(profile: str, region: str):
    """
    Get the S3 client using the specified profile and region.
    """
    session = boto3.Session(profile_name=profile, region_name=region)
    return session.client('s3')

def list_objects(s3_client, bucket_name: str, prefix: str):
    """
    List all objects in an S3 bucket within a specified prefix.
    """
    object_keys = []
    try:
        paginator = s3_client.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix):
            for obj in page.get('Contents', []):
                object_keys.append(obj['Key'])
    except ClientError as e:
        logger.error(f"Error listing objects in bucket {bucket_name} with prefix {prefix}: {e}")
        raise
    return object_keys

def copy_object_with_new_encryption(s3_client, bucket_name: str, object_key: str, kms_key_id: Optional[str] = None, use_sse_s3: bool = False):
    """
    Copy an S3 object to itself using new encryption settings (KMS or SSE-S3).
    """
    try:
        copy_source = {'Bucket': bucket_name, 'Key': object_key}
        extra_args = {}
        if kms_key_id:
            extra_args = {
                'ServerSideEncryption': 'aws:kms',
                'SSEKMSKeyId': kms_key_id
            }
        elif use_sse_s3:
            extra_args = {
                'ServerSideEncryption': 'AES256'
            }
        else:
            logger.warning(f"No encryption method specified for object {object_key}. Skipping.")
            return

        s3_client.copy_object(
            Bucket=bucket_name,
            Key=object_key,
            CopySource=copy_source,
            **extra_args
        )
        logger.info(f"Updated encryption for object {object_key}.")
    except ClientError as e:
        logger.error(f"Error copying object {object_key} in bucket {bucket_name} with new encryption: {e}")
        raise

@app.command()
def main(
    bucket_name: str = typer.Argument(..., help="The name of the S3 bucket."),
    kms_key_id: Optional[str] = typer.Option(None, '--kms-key-id', help="The KMS key ID to use for encryption."),
    sse_s3: bool = typer.Option(False, '--sse-s3', help="Use SSE-S3 for encryption."),
    prefix: str = typer.Option('', '--prefix', help="The prefix of the objects to modify."),
    profile: str = typer.Option('default', '--profile', help="The name of the AWS profile to use."),
    region: str = typer.Option('us-east-1', '--region', help="The AWS region name.")
):
    """
    Update the encryption for objects in an S3 bucket within a specified prefix.
    """
    if not kms_key_id and not sse_s3:
        typer.echo("Error: At least one of --kms-key-id or --sse-s3 must be specified.", err=True)
        raise typer.Exit(code=1)
    try:
        s3_client = get_s3_client(profile, region)
        object_keys = list_objects(s3_client, bucket_name, prefix)

        logger.info(f"Found {len(object_keys)} objects in bucket {bucket_name} with prefix '{prefix}'.")

        for object_key in object_keys:
            copy_object_with_new_encryption(s3_client, bucket_name, object_key, kms_key_id, sse_s3)

        logger.info("All objects updated with the new encryption settings.")
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise typer.Exit(code=1)

if __name__ == '__main__':
    app()
