#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script: update_s3_objects_encryption.py
Description: This script modifies objects in an S3 bucket within a specified prefix to use new encryption settings (KMS or SSE-S3).

Usage:
    python update_s3_objects_encryption.py <bucket_name> [--kms_key_id KMS_KEY_ID] [--sse_s3] [--prefix PREFIX] [--profile PROFILE] [--region REGION]

Arguments:
    bucket_name       The name of the S3 bucket.

Options:
    --kms_key_id KMS_KEY_ID    The KMS key ID to use for encryption.
    --sse_s3                   Use SSE-S3 for encryption.
    --prefix PREFIX            The prefix of the objects to modify (default: '').
    --profile PROFILE          The name of the AWS profile to use (default: default).
    --region REGION            The AWS region name (default: us-east-1).

Requirements:
    - boto3
    - argparse
    - logging
"""

__author__ = "Bradley Kovaluk"
__version__ = "1.0"
__date__ = "2024-07-26"

import boto3
import argparse
import logging
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_s3_client(profile, region):
    """
    Get the S3 client using the specified profile and region.

    Args:
        profile (str): The AWS profile to use.
        region (str): The AWS region to use.

    Returns:
        boto3.client: The S3 client.
    """
    session = boto3.Session(profile_name=profile, region_name=region)
    return session.client('s3')

def list_objects(s3_client, bucket_name, prefix):
    """
    List all objects in an S3 bucket within a specified prefix.

    Args:
        s3_client (boto3.client): The S3 client.
        bucket_name (str): The name of the S3 bucket.
        prefix (str): The prefix of the objects to list.

    Returns:
        list: A list of all object keys in the bucket within the specified prefix.
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

def copy_object_with_new_encryption(s3_client, bucket_name, object_key, kms_key_id=None, use_sse_s3=False):
    """
    Copy an S3 object to itself using new encryption settings (KMS or SSE-S3).

    Args:
        s3_client (boto3.client): The S3 client.
        bucket_name (str): The name of the S3 bucket.
        object_key (str): The key of the object to copy.
        kms_key_id (str, optional): The KMS key ID to use for encryption.
        use_sse_s3 (bool, optional): Whether to use SSE-S3 for encryption.
    """
    try:
        copy_source = {'Bucket': bucket_name, 'Key': object_key}
        if kms_key_id:
            s3_client.copy_object(
                Bucket=bucket_name,
                Key=object_key,
                CopySource=copy_source,
                ServerSideEncryption='aws:kms',
                SSEKMSKeyId=kms_key_id
            )
            logger.info(f"Updated encryption for object {object_key} with KMS key {kms_key_id}.")
        elif use_sse_s3:
            s3_client.copy_object(
                Bucket=bucket_name,
                Key=object_key,
                CopySource=copy_source,
                ServerSideEncryption='AES256'
            )
            logger.info(f"Updated encryption for object {object_key} with SSE-S3.")
        else:
            logger.warning(f"No encryption method specified for object {object_key}. Skipping.")
    except ClientError as e:
        logger.error(f"Error copying object {object_key} in bucket {bucket_name} with new encryption: {e}")
        raise

def main(bucket_name, kms_key_id=None, use_sse_s3=False, prefix='', profile='default', region='us-east-1'):
    """
    Main function to update the encryption for objects in an S3 bucket within a specified prefix.

    Args:
        bucket_name (str): The name of the S3 bucket.
        kms_key_id (str, optional): The KMS key ID to use for encryption.
        use_sse_s3 (bool, optional): Whether to use SSE-S3 for encryption.
        prefix (str): The prefix of the objects to modify.
        profile (str): The AWS profile to use.
        region (str): The AWS region to use.
    """
    try:
        s3_client = get_s3_client(profile, region)
        object_keys = list_objects(s3_client, bucket_name, prefix)

        logger.info(f"Found {len(object_keys)} objects in bucket {bucket_name} with prefix {prefix}.")

        for object_key in object_keys:
            copy_object_with_new_encryption(s3_client, bucket_name, object_key, kms_key_id, use_sse_s3)

        logger.info("All objects updated with the new encryption settings.")
    except Exception as e:
        logger.error(f"Error: {str(e)}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Update the encryption for objects in an S3 bucket within a specified prefix.")
    parser.add_argument('bucket_name', help="The name of the S3 bucket.")
    parser.add_argument('--kms_key_id', help="The KMS key ID to use for encryption.")
    parser.add_argument('--sse_s3', action='store_true', help="Use SSE-S3 for encryption.")
    parser.add_argument('--prefix', default='', help="The prefix of the objects to modify (default: '').")
    parser.add_argument('--profile', default='default', help="The name of the AWS profile to use (default: default).")
    parser.add_argument('--region', default='us-east-1', help="The AWS region name (default: us-east-1).")
    args = parser.parse_args()

    if not args.kms_key_id and not args.sse_s3:
        parser.error("At least one of --kms_key_id or --sse_s3 must be specified.")

    main(args.bucket_name, args.kms_key_id, args.sse_s3, args.prefix, args.profile, args.region)
