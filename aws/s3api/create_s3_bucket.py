#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script: create_s3_bucket.py
Description: This script creates a new S3 bucket with optional configurations including server-side encryption, ACL,
             bucket policy, versioning, logging, and lifecycle rules.

Usage:
    python create_s3_bucket.py <bucket_name> [--sse SSE_TYPE] [--kms-key-id KMS_KEY_ID] [--acl ACL]
                               [--policy POLICY_PATH] [--versioning {enabled,suspended}]
                               [--logging TARGET_BUCKET TARGET_PREFIX] [--lifecycle LIFECYCLE_PATH]
                               [--profile PROFILE] [--region REGION]

Arguments:
    bucket_name        The name of the S3 bucket to create.

Options:
    --sse SSE_TYPE     The type of server-side encryption to use ('s3' for SSE-S3, 'kms' for SSE-KMS).
    --kms-key-id KMS_KEY_ID The ID of the KMS key to use if SSE-KMS is selected (required if --sse is 'kms').
    --acl ACL          The canned ACL to apply to the bucket (e.g., private, public-read).
    --policy POLICY_PATH The path to the bucket policy Jinja2 template file.
    --versioning {enabled,suspended} The versioning state of the bucket.
    --logging TARGET_BUCKET TARGET_PREFIX The target bucket and prefix for server access logging.
    --lifecycle LIFECYCLE_PATH The path to the lifecycle configuration JSON file.
    --profile PROFILE  The name of the AWS profile to use (default: default).
    --region REGION    The AWS region name (default: us-east-1).

Requirements:
    - boto3
    - typer
    - jinja2
    - logging
"""

__author__ = "Bradley Kovaluk"
__version__ = "1.2"
__date__ = "2024-07-01"

import boto3
import logging
import json
from jinja2 import Environment, FileSystemLoader
from botocore.exceptions import ClientError
import typer
from typing import Optional, Tuple

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = typer.Typer(help="Create a new S3 bucket with optional configurations.")

def get_sts_client(profile_name: str, region_name: str):
    """
    Get the STS client using the specified profile and region.
    """
    session = boto3.Session(profile_name=profile_name, region_name=region_name)
    return session.client('sts')

def get_account_id(sts_client):
    """
    Get the AWS account ID using STS.
    """
    try:
        identity = sts_client.get_caller_identity()
        return identity['Account']
    except ClientError as e:
        logger.error(f"Error getting account ID: {e}")
        raise

def render_policy(template_path: str, parameters: dict) -> str:
    """
    Render the bucket policy using the Jinja2 template and provided parameters.
    """
    env = Environment(loader=FileSystemLoader('.'))
    template = env.get_template(template_path)
    return template.render(parameters)

def create_bucket(s3_client, bucket_name: str, acl: Optional[str], bucket_configuration: dict):
    """
    Create the S3 bucket with the specified name and ACL.
    """
    try:
        params = {'Bucket': bucket_name}
        if acl:
            params['ACL'] = acl
        params.update(bucket_configuration)
        s3_client.create_bucket(**params)
        logger.info(f"Created S3 bucket: {bucket_name}")
    except s3_client.exceptions.BucketAlreadyExists:
        logger.error(f"Bucket {bucket_name} already exists.")
        raise
    except s3_client.exceptions.BucketAlreadyOwnedByYou:
        logger.error(f"Bucket {bucket_name} is already owned by you.")
        raise
    except Exception as e:
        logger.error(f"Error creating bucket {bucket_name}: {str(e)}")
        raise

def configure_bucket_encryption(s3_client, bucket_name: str, sse_type: str, kms_key_id: Optional[str]):
    """
    Configure server-side encryption for the S3 bucket.
    """
    try:
        encryption_configuration = {
            'Rules': [{
                'ApplyServerSideEncryptionByDefault': {
                    'SSEAlgorithm': 'AES256' if sse_type == 's3' else 'aws:kms'
                }
            }]
        }
        if sse_type == 'kms' and kms_key_id:
            encryption_configuration['Rules'][0]['ApplyServerSideEncryptionByDefault']['KMSMasterKeyID'] = kms_key_id

        s3_client.put_bucket_encryption(
            Bucket=bucket_name,
            ServerSideEncryptionConfiguration=encryption_configuration
        )
        logger.info(f"Enabled {sse_type.upper()} encryption on bucket: {bucket_name}")
    except Exception as e:
        logger.error(f"Error configuring encryption on bucket {bucket_name}: {str(e)}")
        raise

def apply_bucket_policy(s3_client, bucket_name: str, policy_path: str, account_id: str, region_name: str, kms_key_id: Optional[str]):
    """
    Apply the bucket policy to the S3 bucket.
    """
    try:
        kms_key_arn = f"arn:aws:kms:{region_name}:{account_id}:key/{kms_key_id}" if kms_key_id else ''
        policy_parameters = {
            'account_id': account_id,
            'bucket_name': bucket_name,
            'kms_key_arn': kms_key_arn
        }
        policy = render_policy(policy_path, policy_parameters)
        s3_client.put_bucket_policy(Bucket=bucket_name, Policy=policy)
        logger.info(f"Applied bucket policy from {policy_path} to bucket: {bucket_name}")
    except Exception as e:
        logger.error(f"Error applying bucket policy to bucket {bucket_name}: {str(e)}")
        raise

def configure_bucket_versioning(s3_client, bucket_name: str, versioning: str):
    """
    Configure versioning for the S3 bucket.
    """
    try:
        s3_client.put_bucket_versioning(
            Bucket=bucket_name,
            VersioningConfiguration={'Status': versioning.capitalize()}
        )
        logger.info(f"Set versioning to {versioning} on bucket: {bucket_name}")
    except Exception as e:
        logger.error(f"Error configuring versioning on bucket {bucket_name}: {str(e)}")
        raise

def configure_bucket_logging(s3_client, bucket_name: str, logging_config: Tuple[str, str]):
    """
    Configure server access logging for the S3 bucket.
    """
    try:
        target_bucket, target_prefix = logging_config
        s3_client.put_bucket_logging(
            Bucket=bucket_name,
            BucketLoggingStatus={
                'LoggingEnabled': {
                    'TargetBucket': target_bucket,
                    'TargetPrefix': target_prefix
                }
            }
        )
        logger.info(f"Enabled logging on bucket: {bucket_name} to target bucket: {target_bucket} with prefix: {target_prefix}")
    except Exception as e:
        logger.error(f"Error configuring logging on bucket {bucket_name}: {str(e)}")
        raise

def configure_bucket_lifecycle(s3_client, bucket_name: str, lifecycle_path: str):
    """
    Configure lifecycle rules for the S3 bucket.
    """
    try:
        with open(lifecycle_path, 'r') as lifecycle_file:
            lifecycle = json.load(lifecycle_file)
        s3_client.put_bucket_lifecycle_configuration(
            Bucket=bucket_name,
            LifecycleConfiguration=lifecycle
        )
        logger.info(f"Applied lifecycle configuration from {lifecycle_path} to bucket: {bucket_name}")
    except Exception as e:
        logger.error(f"Error configuring lifecycle on bucket {bucket_name}: {str(e)}")
        raise

def main(
    bucket_name: str,
    sse: Optional[str] = typer.Option(None, "--sse", help="The type of server-side encryption to use ('s3' for SSE-S3, 'kms' for SSE-KMS)."),
    kms_key_id: Optional[str] = typer.Option(None, "--kms-key-id", help="The ID of the KMS key to use if SSE-KMS is selected (required if --sse is 'kms')."),
    acl: Optional[str] = typer.Option(None, "--acl", help="The canned ACL to apply to the bucket (e.g., private, public-read)."),
    policy: Optional[str] = typer.Option(None, "--policy", help="The path to the bucket policy Jinja2 template file."),
    versioning: Optional[str] = typer.Option(None, "--versioning", help="The versioning state of the bucket ('enabled' or 'suspended')."),
    logging_config: Optional[Tuple[str, str]] = typer.Option(None, "--logging", help="The target bucket and prefix for server access logging.", nargs=2),
    lifecycle: Optional[str] = typer.Option(None, "--lifecycle", help="The path to the lifecycle configuration JSON file."),
    profile: str = typer.Option("default", "--profile", help="The name of the AWS profile to use (default: default)."),
    region: str = typer.Option("us-east-1", "--region", help="The AWS region name (default: us-east-1).")
):
    """
    Create a new S3 bucket with optional configurations.
    """
    if sse == 'kms' and not kms_key_id:
        typer.echo("Error: --kms-key-id is required if --sse is 'kms'.", err=True)
        raise typer.Exit(code=1)
    if versioning and versioning not in ['enabled', 'suspended']:
        typer.echo("Error: --versioning must be 'enabled' or 'suspended'.", err=True)
        raise typer.Exit(code=1)

    session = boto3.Session(profile_name=profile, region_name=region)
    s3_client = session.client('s3')
    sts_client = get_sts_client(profile, region)
    account_id = get_account_id(sts_client)

    bucket_configuration = {}
    if region != 'us-east-1':
        bucket_configuration['CreateBucketConfiguration'] = {
            'LocationConstraint': region
        }

    try:
        create_bucket(s3_client, bucket_name, acl, bucket_configuration)

        if sse:
            configure_bucket_encryption(s3_client, bucket_name, sse, kms_key_id)

        if policy:
            apply_bucket_policy(s3_client, bucket_name, policy, account_id, region, kms_key_id)

        if versioning:
            configure_bucket_versioning(s3_client, bucket_name, versioning)

        if logging_config:
            configure_bucket_logging(s3_client, bucket_name, logging_config)

        if lifecycle:
            configure_bucket_lifecycle(s3_client, bucket_name, lifecycle)
    except Exception as e:
        logger.error(f"Failed to create bucket '{bucket_name}': {str(e)}")
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app.command()(main)
    app()
