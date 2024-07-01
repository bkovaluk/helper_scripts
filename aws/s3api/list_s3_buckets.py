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
    - argparse
    - logging
"""

__author__ = "Bradley Kovaluk"
__version__ = "1.0"
__date__ = "2024-07-01"

import boto3
import argparse
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def list_s3_buckets(profile_name, region_name='us-east-1', substring=None):
    """List all S3 buckets in the AWS account, optionally filtering by a substring."""
    session = boto3.Session(profile_name=profile_name, region_name=region_name)
    s3_client = session.client('s3')

    response = s3_client.list_buckets()
    buckets = response['Buckets']

    if substring:
        buckets = [bucket for bucket in buckets if substring in bucket['Name']]

    logger.info("S3 Buckets:")
    for bucket in buckets:
        logger.info(bucket['Name'])

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="List all S3 buckets in your AWS account, optionally filtering by a substring")
    parser.add_argument("--substring", help="The substring to filter bucket names (default: None)")
    parser.add_argument("--profile", default="default", help="The name of the AWS profile to use (default: default)")
    parser.add_argument("--region", default="us-east-1", help="The AWS region name (default: us-east-1)")

    args = parser.parse_args()

    list_s3_buckets(
        profile_name=args.profile,
        region_name=args.region,
        substring=args.substring
    )
