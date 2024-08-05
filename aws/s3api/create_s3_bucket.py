#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script: create_s3_bucket.py
Description: This script creates a new S3 bucket with optional configurations including server-side encryption, ACL,
             bucket policy, versioning, logging, and lifecycle rules.

Usage:
    python create_s3_bucket.py <bucket_name> [--sse SSE_TYPE] [--kms_key_id KMS_KEY_ID] [--acl ACL]
                               [--policy POLICY_PATH] [--versioning {enabled,suspended}]
                               [--logging TARGET_BUCKET TARGET_PREFIX] [--lifecycle LIFECYCLE_PATH]
                               [--profile PROFILE] [--region REGION]

Arguments:
    bucket_name        The name of the S3 bucket to create.

Options:
    --sse SSE_TYPE     The type of server-side encryption to use ('s3' for SSE-S3, 'kms' for SSE-KMS).
    --kms_key_id KMS_KEY_ID The ID of the KMS key to use if SSE-KMS is selected (required if --sse is 'kms').
    --acl ACL          The canned ACL to apply to the bucket (e.g., private, public-read).
    --policy POLICY_PATH The path to the bucket policy Jinja2 template file.
    --versioning {enabled,suspended} The versioning state of the bucket.
    --logging TARGET_BUCKET TARGET_PREFIX The target bucket and prefix for server access logging.
    --lifecycle LIFECYCLE_PATH The path to the lifecycle configuration JSON file.
    --profile PROFILE  The name of the AWS profile to use (default: default).
    --region REGION    The AWS region name (default: us-east-1).

Requirements:
    - boto3
    - argparse
    - jinja2
    - logging
"""

__author__ = "Bradley Kovaluk"
__version__ = "1.1"
__date__ = "2024-07-01"

import boto3
import argparse
import logging
import json
from jinja2 import Environment, FileSystemLoader
from botocore.exceptions import ClientError

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_sts_client(profile_name, region_name):
    """
    Get the STS client using the specified profile and region.

    Args:
        profile_name (str): The AWS profile to use.
        region_name (str): The AWS region to use.

    Returns:
        boto3.client: The STS client.
    """
    session = boto3.Session(profile_name=profile_name, region_name=region_name)
    return session.client('sts')

def get_account_id(sts_client):
    """
    Get the AWS account ID using STS.

    Args:
        sts_client (boto3.client): The STS client.

    Returns:
        str: The AWS account ID.
    """
    try:
        identity = sts_client.get_caller_identity()
        return identity['Account']
    except ClientError as e:
        logger.error(f"Error getting account ID: {e}")
        raise

def render_policy(template_path, parameters):
    """
    Render the bucket policy using the Jinja2 template and provided parameters.

    Args:
        template_path (str): The path to the Jinja2 template file.
        parameters (dict): A dictionary of parameters to pass to the template.

    Returns:
        str: The rendered bucket policy.
    """
    env = Environment(loader=FileSystemLoader('.'))
    template = env.get_template(template_path)
    return template.render(parameters)

def create_bucket(s3_client, bucket_name, acl, bucket_configuration):
    """
    Create the S3 bucket with the specified name and ACL.

    Args:
        s3_client (boto3.client): The S3 client.
        bucket_name (str): The name of the S3 bucket.
        acl (str): The canned ACL to apply to the bucket.
        bucket_configuration (dict): Additional bucket configuration.

    Raises:
        Exception: If the bucket creation fails.
    """
    try:
        s3_client.create_bucket(Bucket=bucket_name, ACL=acl, **bucket_configuration)
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

def configure_bucket_encryption(s3_client, bucket_name, sse_type, kms_key_id):
    """
    Configure server-side encryption for the S3 bucket.

    Args:
        s3_client (boto3.client): The S3 client.
        bucket_name (str): The name of the S3 bucket.
        sse_type (str): The type of server-side encryption to use.
        kms_key_id (str): The ID of the KMS key to use if SSE-KMS is selected.

    Raises:
        Exception: If the encryption configuration fails.
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

def apply_bucket_policy(s3_client, bucket_name, policy_path, account_id, region_name, kms_key_id):
    """
    Apply the bucket policy to the S3 bucket.

    Args:
        s3_client (boto3.client): The S3 client.
        bucket_name (str): The name of the S3 bucket.
        policy_path (str): The path to the bucket policy Jinja2 template file.
        account_id (str): The AWS account ID.
        region_name (str): The AWS region name.
        kms_key_id (str): The ID of the KMS key to use if SSE-KMS is selected.

    Raises:
        Exception: If applying the bucket policy fails.
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

def configure_bucket_versioning(s3_client, bucket_name, versioning):
    """
    Configure versioning for the S3 bucket.

    Args:
        s3_client (boto3.client): The S3 client.
        bucket_name (str): The name of the S3 bucket.
        versioning (str): The versioning state of the bucket.

    Raises:
        Exception: If configuring bucket versioning fails.
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

def configure_bucket_logging(s3_client, bucket_name, logging_config):
    """
    Configure server access logging for the S3 bucket.

    Args:
        s3_client (boto3.client): The S3 client.
        bucket_name (str): The name of the S3 bucket.
        logging_config (tuple): The target bucket and prefix for server access logging.

    Raises:
        Exception: If configuring bucket logging fails.
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

def configure_bucket_lifecycle(s3_client, bucket_name, lifecycle_path):
    """
    Configure lifecycle rules for the S3 bucket.

    Args:
        s3_client (boto3.client): The S3 client.
        bucket_name (str): The name of the S3 bucket.
        lifecycle_path (str): The path to the lifecycle configuration JSON file.

    Raises:
        Exception: If configuring bucket lifecycle rules fails.
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

def main(bucket_name, sse_type, kms_key_id, acl, policy_path, versioning, logging_config, lifecycle_path, profile_name, region_name='us-east-1'):
    """
    Main function to create a new S3 bucket with optional configurations.

    Args:
        bucket_name (str): The name of the S3 bucket to create.
        sse_type (str): The type of server-side encryption to use.
        kms_key_id (str): The ID of the KMS key to use if SSE-KMS is selected.
        acl (str): The canned ACL to apply to the bucket.
        policy_path (str): The path to the bucket policy Jinja2 template file.
        versioning (str): The versioning state of the bucket.
        logging_config (tuple): The target bucket and prefix for server access logging.
        lifecycle_path (str): The path to the lifecycle configuration JSON file.
        profile_name (str): The name of the AWS profile to use.
        region_name (str): The AWS region name.
    """
    session = boto3.Session(profile_name=profile_name, region_name=region_name)
    s3_client = session.client('s3')
    sts_client = get_sts_client(profile_name, region_name)
    account_id = get_account_id(sts_client)

    bucket_configuration = {}
    if region_name != 'us-east-1':
        bucket_configuration['CreateBucketConfiguration'] = {
            'LocationConstraint': region_name
        }

    create_bucket(s3_client, bucket_name, acl, bucket_configuration)

    if sse_type:
        configure_bucket_encryption(s3_client, bucket_name, sse_type, kms_key_id)

    if policy_path:
        apply_bucket_policy(s3_client, bucket_name, policy_path, account_id, region_name, kms_key_id)

    if versioning:
        configure_bucket_versioning(s3_client, bucket_name, versioning)

    if logging_config:
        configure_bucket_logging(s3_client, bucket_name, logging_config)

    if lifecycle_path:
        configure_bucket_lifecycle(s3_client, bucket_name, lifecycle_path)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create a new S3 bucket with optional configurations")
    parser.add_argument("bucket_name", help="The name of the S3 bucket to create")
    parser.add_argument("--sse", choices=['s3', 'kms'], help="The type of server-side encryption to use ('s3' for SSE-S3, 'kms' for SSE-KMS)")
    parser.add_argument("--kms_key_id", help="The ID of the KMS key to use if SSE-KMS is selected (required if --sse is 'kms')")
    parser.add_argument("--acl", help="The canned ACL to apply to the bucket (e.g., private, public-read)")
    parser.add_argument("--policy", help="The path to the bucket policy Jinja2 template file")
    parser.add_argument("--versioning", choices=['enabled', 'suspended'], help="The versioning state of the bucket")
    parser.add_argument("--logging", nargs=2, metavar=('TARGET_BUCKET', 'TARGET_PREFIX'), help="The target bucket and prefix for server access logging")
    parser.add_argument("--lifecycle", help="The path to the lifecycle configuration JSON file")
    parser.add_argument("--profile", default="default", help="The name of the AWS profile to use (default: default)")
    parser.add_argument("--region", default="us-east-1", help="The AWS region name (default: us-east-1)")

    args = parser.parse_args()

    if args.sse == 'kms' and not args.kms_key_id:
        parser.error("--kms_key_id is required if --sse is 'kms'")

    main(
        bucket_name=args.bucket_name,
        sse_type=args.sse,
        kms_key_id=args.kms_key_id,
        acl=args.acl,
        policy_path=args.policy,
        versioning=args.versioning,
        logging_config=args.logging,
        lifecycle_path=args.lifecycle,
        profile_name=args.profile,
        region_name=args.region
    )
