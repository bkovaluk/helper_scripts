#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script: create_managed_policy.py
Description: This script creates an AWS IAM managed policy using a Jinja2 template.
             It reads the policy template from a specified file, renders it with
             the AWS account ID and region, and creates a managed policy in AWS IAM.

Usage:
    python create_managed_policy.py <policy_name> <policy_template_path> [--profile PROFILE] [--region REGION]

Arguments:
    policy_name         The name of the managed policy.
    policy_template_path The path to the Jinja2 template file inside the 'policies' directory.

Options:
    --profile PROFILE   The name of the AWS profile to use (default: default).
    --region REGION     The AWS region name (default: us-east-1).

Requirements:
    - boto3
    - argparse
    - os
    - jinja2
    - logging
"""

__author__ = "Bradley Kovaluk"
__version__ = "1.0"
__date__ = "2023-02-15"

import boto3
import argparse
from jinja2 import Environment, FileSystemLoader
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_account_id(session):
    """Get AWS account ID using STS."""
    sts_client = session.client("sts")
    identity = sts_client.get_caller_identity()
    return identity["Account"]


def create_managed_policy(
    policy_name, policy_template_path, profile_name, region_name="us-east-1"
):
    """Create a managed policy using a Jinja2 template."""
    # Set up Jinja2 environment and load template
    env = Environment(loader=FileSystemLoader("policies"))
    template = env.get_template(policy_template_path)

    # Set up Boto3 session
    session = boto3.Session(profile_name=profile_name, region_name=region_name)
    logger.info(f"Using AWS profile: {profile_name} in region: {region_name}")

    # Get the AWS account ID
    account_id = get_account_id(session)
    logger.info(f"Retrieved AWS account ID: {account_id}")

    # Render the policy document using the template
    policy_document = template.render(
        region=region_name,
        account_id=account_id,
    )

    iam_client = session.client("iam")

    # Create the managed policy
    response = iam_client.create_policy(
        PolicyName=policy_name,
        PolicyDocument=policy_document,
    )
    logger.info(f"Created managed policy: {policy_name}")

    return response


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Create a managed policy using a Jinja2 template"
    )
    parser.add_argument("policy_name", help="The name of the managed policy")
    parser.add_argument(
        "policy_template_path",
        help="The path to the Jinja2 template file inside the 'policies' directory",
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

    response = create_managed_policy(
        policy_name=args.policy_name,
        policy_template_path=args.policy_template_path,
        profile_name=args.profile,
        region_name=args.region,
    )

    print(response)
