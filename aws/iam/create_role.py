#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script: create_role.py
Description: This script creates an AWS IAM role using a Jinja2 template for the trust policy.
             It reads the trust policy template from a specified file, renders it with
             the AWS account ID and region, and creates the role in AWS IAM.

Usage:
    python create_role.py <role_name> <trust_policy_template_path> [--profile PROFILE] [--region REGION] [--description DESCRIPTION]

Arguments:
    role_name                The name of the IAM role to create.
    trust_policy_template_path The path to the Jinja2 template file for the trust policy inside the 'policies' directory.

Options:
    --profile PROFILE        The name of the AWS profile to use (default: default).
    --region REGION          The AWS region name (default: us-east-1).
    --description DESCRIPTION The description of the role (default: None).

Requirements:
    - boto3
    - argparse
    - os
    - jinja2
    - logging
"""

__author__ = "Bradley Kovaluk"
__version__ = "1.0"
__date__ = "2023-04-21"

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


def create_role(
    role_name,
    trust_policy_template_path,
    profile_name,
    region_name="us-east-1",
    description=None,
):
    """Create a role using a Jinja2 template for the trust policy."""
    # Set up Jinja2 environment and load template
    env = Environment(loader=FileSystemLoader("policies"))
    template = env.get_template(trust_policy_template_path)

    # Set up Boto3 session
    session = boto3.Session(profile_name=profile_name, region_name=region_name)
    logger.info(f"Using AWS profile: {profile_name} in region: {region_name}")

    # Get the AWS account ID
    account_id = get_account_id(session)
    logger.info(f"Retrieved AWS account ID: {account_id}")

    # Render the trust policy document using the template
    trust_policy_document = template.render(
        region=region_name,
        account_id=account_id,
    )

    iam_client = session.client("iam")

    # Create the role
    response = iam_client.create_role(
        RoleName=role_name,
        AssumeRolePolicyDocument=trust_policy_document,
        Description=description,
    )
    logger.info(f"Created role: {role_name}")

    return response


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Create a role using a Jinja2 template for the trust policy"
    )
    parser.add_argument("role_name", help="The name of the IAM role to create")
    parser.add_argument(
        "trust_policy_template_path",
        help="The path to the Jinja2 template file for the trust policy inside the 'policies' directory",
    )
    parser.add_argument(
        "--profile",
        default="default",
        help="The name of the AWS profile to use (default: default)",
    )
    parser.add_argument(
        "--region", default="us-east-1", help="The AWS region name (default: us-east-1)"
    )
    parser.add_argument(
        "--description", help="The description of the role (default: None)"
    )

    args = parser.parse_args()

    response = create_role(
        role_name=args.role_name,
        trust_policy_template_path=args.trust_policy_template_path,
        profile_name=args.profile,
        region_name=args.region,
        description=args.description,
    )

    print(response)
