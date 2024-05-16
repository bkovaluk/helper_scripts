#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script: list_attached_policies.py
Description: This script lists all managed policies attached to an IAM role.

Usage:
    python list_attached_policies.py <role_name> [--profile PROFILE] [--region REGION]

Arguments:
    role_name         The name of the IAM role to list attached policies for.

Options:
    --profile PROFILE The name of the AWS profile to use (default: default).
    --region REGION   The AWS region name (default: us-east-1).

Requirements:
    - boto3
    - argparse
    - logging
"""

__author__ = "Bradley Kovaluk"
__version__ = "1.0"
__date__ = "2024-01-15"

import boto3
import argparse
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def list_attached_policies(role_name, profile_name, region_name="us-east-1"):
    """List all managed policies attached to an IAM role."""
    session = boto3.Session(profile_name=profile_name, region_name=region_name)
    iam_client = session.client("iam")

    response = iam_client.list_attached_role_policies(
        RoleName=role_name,
    )

    policies = response["AttachedPolicies"]
    for policy in policies:
        logger.info(
            f"Policy ARN: {policy['PolicyArn']} Policy Name: {policy['PolicyName']}"
        )

    return policies


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="List all managed policies attached to an IAM role"
    )
    parser.add_argument(
        "role_name", help="The name of the IAM role to list attached policies for"
    )
    parser.add_argument(
        "--profile",
        default="default",
        help="The name of the AWS profile to use (default: default)",
    )
    parser.add_argument(
        "--region", default="us-east-1", help="The AWS region name (default: us-east-1)"
    )

    args = parser.parse_args()

    policies = list_attached_policies(
        role_name=args.role_name,
        profile_name=args.profile,
        region_name=args.region,
    )

    for policy in policies:
        print(f"Policy ARN: {policy['PolicyArn']} Policy Name: {policy['PolicyName']}")
