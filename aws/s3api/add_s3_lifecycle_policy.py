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
    - argparse
    - logging
"""

__author__ = "Bradley Kovaluk"
__version__ = "1.0"
__date__ = "2024-07-02"

import boto3
import argparse
import logging
import json

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def add_s3_lifecycle_policy(bucket_name, lifecycle_policy_path, profile_name, region_name='us-east-1'):
    """Add a lifecycle policy to an S3 bucket."""
    session = boto3.Session(profile_name=profile_name, region_name=region_name)
    s3_client = session.client('s3')

    # Read lifecycle policy from the specified file
    with open(lifecycle_policy_path, 'r') as policy_file:
        lifecycle_policy = json.load(policy_file)

    try:
        # Put lifecycle policy on the bucket
        s3_client.put_bucket_lifecycle_configuration(
            Bucket=bucket_name,
            LifecycleConfiguration=lifecycle_policy
        )
        logger.info(f"Applied lifecycle policy from {lifecycle_policy_path} to bucket: {bucket_name}")
    except Exception as e:
        logger.error(f"Error applying lifecycle policy to bucket {bucket_name}: {str(e)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Add a lifecycle policy to an S3 bucket")
    parser.add_argument("bucket_name", help="The name of the S3 bucket")
    parser.add_argument("lifecycle_policy_path", help="The path to the lifecycle policy JSON file")
    parser.add_argument("--profile", default="default", help="The name of the AWS profile to use (default: default)")
    parser.add_argument("--region", default="us-east-1", help="The AWS region name (default: us-east-1)")

    args = parser.parse_args()

    add_s3_lifecycle_policy(
        bucket_name=args.bucket_name,
        lifecycle_policy_path=args.lifecycle_policy_path,
        profile_name=args.profile,
        region_name=args.region
    )
