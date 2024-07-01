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
    --policy POLICY_PATH The path to the bucket policy JSON file.
    --versioning {enabled,suspended} The versioning state of the bucket.
    --logging TARGET_BUCKET TARGET_PREFIX The target bucket and prefix for server access logging.
    --lifecycle LIFECYCLE_PATH The path to the lifecycle configuration JSON file.
    --profile PROFILE  The name of the AWS profile to use (default: default).
    --region REGION    The AWS region name (default: us-east-1).

Requirements:
    - boto3
    - argparse
    - logging
"""

__author__ = "Bradley Kovaluk"
__version__ = "1.0"
__date__ = "2024-07-01"

import boto3
import argparse
import logging
import json

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_s3_bucket(bucket_name, sse_type, kms_key_id, acl, policy_path, versioning, logging_config, lifecycle_path, profile_name, region_name='us-east-1'):
    """Create a new S3 bucket with optional configurations."""
    session = boto3.Session(profile_name=profile_name, region_name=region_name)
    s3_client = session.client('s3')

    bucket_configuration = {}
    if region_name != 'us-east-1':
        bucket_configuration['CreateBucketConfiguration'] = {
            'LocationConstraint': region_name
        }

    try:
        s3_client.create_bucket(Bucket=bucket_name, ACL=acl, **bucket_configuration)
        logger.info(f"Created S3 bucket: {bucket_name}")

        if sse_type:
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

        if policy_path:
            with open(policy_path, 'r') as policy_file:
                policy = json.load(policy_file)
            s3_client.put_bucket_policy(Bucket=bucket_name, Policy=json.dumps(policy))
            logger.info(f"Applied bucket policy from {policy_path} to bucket: {bucket_name}")

        if versioning:
            s3_client.put_bucket_versioning(
                Bucket=bucket_name,
                VersioningConfiguration={'Status': versioning.capitalize()}
            )
            logger.info(f"Set versioning to {versioning} on bucket: {bucket_name}")

        if logging_config:
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

        if lifecycle_path:
            with open(lifecycle_path, 'r') as lifecycle_file:
                lifecycle = json.load(lifecycle_file)
            s3_client.put_bucket_lifecycle_configuration(
                Bucket=bucket_name,
                LifecycleConfiguration=lifecycle
            )
            logger.info(f"Applied lifecycle configuration from {lifecycle_path} to bucket: {bucket_name}")

    except s3_client.exceptions.BucketAlreadyExists as e:
        logger.error(f"Bucket {bucket_name} already exists.")
    except s3_client.exceptions.BucketAlreadyOwnedByYou as e:
        logger.error(f"Bucket {bucket_name} is already owned by you.")
    except Exception as e:
        logger.error(f"Error creating bucket {bucket_name}: {str(e)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create a new S3 bucket with optional configurations")
    parser.add_argument("bucket_name", help="The name of the S3 bucket to create")
    parser.add_argument("--sse", choices=['s3', 'kms'], help="The type of server-side encryption to use ('s3' for SSE-S3, 'kms' for SSE-KMS)")
    parser.add_argument("--kms_key_id", help="The ID of the KMS key to use if SSE-KMS is selected (required if --sse is 'kms')")
    parser.add_argument("--acl", help="The canned ACL to apply to the bucket (e.g., private, public-read)")
    parser.add_argument("--policy", help="The path to the bucket policy JSON file")
    parser.add_argument("--versioning", choices=['enabled', 'suspended'], help="The versioning state of the bucket")
    parser.add_argument("--logging", nargs=2, metavar=('TARGET_BUCKET', 'TARGET_PREFIX'), help="The target bucket and prefix for server access logging")
    parser.add_argument("--lifecycle", help="The path to the lifecycle configuration JSON file")
    parser.add_argument("--profile", default="default", help="The name of the AWS profile to use (default: default)")
    parser.add_argument("--region", default="us-east-1", help="The AWS region name (default: us-east-1)")

    args = parser.parse_args()

    if args.sse == 'kms' and not args.kms_key_id:
        parser.error("--kms_key_id is required if --sse is 'kms'")

    create_s3_bucket(
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
