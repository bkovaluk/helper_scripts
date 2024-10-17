#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script: list_iam_roles_without_inline_policy.py
Description: This script returns a list of IAM roles that do not have a specified inline policy attached.
             The script takes an inline policy name and an optional regex pattern for IAM role names as arguments.

Usage:
    python list_iam_roles_without_inline_policy.py <inline_policy_name> [<role_regex>] [--profile PROFILE] [--region REGION]

Arguments:
    inline_policy_name The name of the inline policy to check for.
    role_regex         (Optional) The regex pattern to match IAM roles (e.g., ^APP_). If not provided, all roles will be checked.

Options:
    --profile PROFILE The name of the AWS profile to use (default: default).
    --region REGION   The AWS region name (default: us-east-1).

Requirements:
    - boto3
    - typer
    - re
    - logging
"""

__author__ = "Bradley Kovaluk"
__version__ = "1.6"
__date__ = "2024-07-11"

import boto3
import logging
import re
import typer
from typing import Optional
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(
    level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = typer.Typer(
    help="List IAM roles without a specified inline policy attached."
)


def get_iam_client(profile, region):
    """Get the IAM client using the specified profile and region."""
    session = boto3.Session(profile_name=profile, region_name=region)
    return session.client('iam')


def get_iam_roles(iam_client, role_regex=None):
    """Get a list of IAM roles matching the specified regex pattern."""
    paginator = iam_client.get_paginator('list_roles')
    roles = []

    pattern = re.compile(role_regex) if role_regex else None

    for page in paginator.paginate():
        for role in page['Roles']:
            if pattern is None or pattern.match(role['RoleName']):
                roles.append(role['RoleName'])

    return roles


def role_has_inline_policy(iam_client, role_name, inline_policy_name):
    """Check if the specified IAM role has the given inline policy attached."""
    paginator = iam_client.get_paginator('list_role_policies')
    for page in paginator.paginate(RoleName=role_name):
        if inline_policy_name in page['PolicyNames']:
            return True
    return False


@app.command()
def main(
    inline_policy_name: str = typer.Argument(
        ..., help="The name of the inline policy to check for."
    ),
    role_regex: Optional[str] = typer.Argument(
        None,
        help="The regex pattern to match IAM roles. If not provided, all roles will be checked."
    ),
    profile: str = typer.Option(
        'default',
        help="The name of the AWS profile to use (default: default)."
    ),
    region: str = typer.Option(
        'us-east-1',
        help="The AWS region name (default: us-east-1)."
    ),
):
    """
    List IAM roles without a specified inline policy attached.
    """
    try:
        iam_client = get_iam_client(profile, region)

        roles = get_iam_roles(iam_client, role_regex)
        logger.info(f"Found {len(roles)} roles matching regex '{role_regex}'.")

        roles_without_policy = [role for role in roles if not role_has_inline_policy(iam_client, role, inline_policy_name)]

        logger.info(f"Found {len(roles_without_policy)} roles without the inline policy '{inline_policy_name}':")
        for role in roles_without_policy:
            logger.info(role)

    except ClientError as e:
        logger.error(f"AWS ClientError: {e}")
    except Exception as e:
        logger.error(f"Error: {str(e)}")


if __name__ == '__main__':
    app()
