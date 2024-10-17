#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script: list_iam_roles_with_policy.py
Description: This script returns a list of IAM roles that have a specified managed policy attached.
             It also shows for each role the inline policies' total character length and managed policy count,
             and how close they are to AWS IAM limits.

Usage:
    python list_iam_roles_with_policy.py <managed_policy_name> [<role_regex>] [--profile PROFILE] [--region REGION]

Arguments:
    managed_policy_name The name of the managed policy to check for.
    role_regex          (Optional) The regex pattern to match IAM roles (e.g., ^APP_). If not provided, all roles will be checked.

Options:
    --profile PROFILE   The name of the AWS profile to use (default: default).
    --region REGION     The AWS region name (default: us-east-1).

Requirements:
    - boto3
    - typer
    - tabulate
    - re
    - logging
"""

__author__ = "Bradley Kovaluk"
__version__ = "1.4"
__date__ = "2024-07-11"

import boto3
import logging
import re
import sys
import typer
from typing import List, Tuple, Optional
from tabulate import tabulate
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

app = typer.Typer(help="List IAM roles with a specified managed policy attached.")

# AWS IAM Limits
INLINE_POLICY_SIZE_LIMIT = 10240  # 10,240 characters
MANAGED_POLICY_LIMIT = 10  # Maximum number of managed policies per role

def get_iam_client(profile: str, region: str):
    """
    Get the IAM client with the specified profile and region.

    Args:
        profile (str): The AWS profile to use.
        region (str): The AWS region to use.

    Returns:
        boto3.client: The IAM client.
    """
    session = boto3.Session(profile_name=profile, region_name=region)
    return session.client('iam')

def get_policy_arn(iam_client, policy_name: str):
    """
    Get the ARN of the specified managed policy.

    Args:
        iam_client (boto3.client): The IAM client.
        policy_name (str): The name of the managed policy.

    Returns:
        str: The ARN of the managed policy.
    """
    paginator = iam_client.get_paginator('list_policies')
    for page in paginator.paginate(Scope='All', OnlyAttached=False):
        for policy in page['Policies']:
            if policy['PolicyName'] == policy_name:
                return policy['Arn']

    raise ValueError(f"Managed policy '{policy_name}' not found.")

def list_roles_with_policy(iam_client, policy_arn: str, role_regex: Optional[str] = None) -> List[str]:
    """
    List IAM roles that have the specified managed policy attached.

    Args:
        iam_client (boto3.client): The IAM client.
        policy_arn (str): The ARN of the managed policy.
        role_regex (str): The regex pattern to match IAM roles. If None, all roles are checked.

    Returns:
        list: A list of IAM role names that have the managed policy attached.
    """
    roles_with_policy = []

    paginator = iam_client.get_paginator('list_entities_for_policy')
    pattern = re.compile(role_regex) if role_regex else None

    for page in paginator.paginate(PolicyArn=policy_arn, EntityFilter='Role'):
        for role in page.get('PolicyRoles', []):
            role_name = role['RoleName']
            if pattern is None or pattern.match(role_name):
                roles_with_policy.append(role_name)

    return roles_with_policy

def get_inline_policies(iam_client, role_name: str) -> Tuple[int, int]:
    """
    Get the total character length of all inline policies attached to a role.

    Args:
        iam_client (boto3.client): The IAM client.
        role_name (str): The name of the IAM role.

    Returns:
        Tuple[int, int]: Total character length and number of inline policies.
    """
    total_length = 0
    policy_count = 0
    paginator = iam_client.get_paginator('list_role_policies')
    for page in paginator.paginate(RoleName=role_name):
        for policy_name in page['PolicyNames']:
            policy = iam_client.get_role_policy(RoleName=role_name, PolicyName=policy_name)
            policy_document = policy['PolicyDocument']
            policy_json = json.dumps(policy_document, separators=(',', ':'))
            length = len(policy_json)
            total_length += length
            policy_count += 1
    return total_length, policy_count

def get_managed_policy_count(iam_client, role_name: str) -> int:
    """
    Get the count of managed policies attached to a role.

    Args:
        iam_client (boto3.client): The IAM client.
        role_name (str): The name of the IAM role.

    Returns:
        int: Number of managed policies attached to the role.
    """
    count = 0
    paginator = iam_client.get_paginator('list_attached_role_policies')
    for page in paginator.paginate(RoleName=role_name):
        count += len(page['AttachedPolicies'])
    return count

@app.command()
def main(
    managed_policy_name: str = typer.Argument(..., help="The name of the managed policy to check for."),
    role_regex: Optional[str] = typer.Argument(None, help="The regex pattern to match IAM roles. If not provided, all roles will be checked."),
    profile: str = typer.Option('default', help="The name of the AWS profile to use (default: default)."),
    region: str = typer.Option('us-east-1', help="The AWS region name (default: us-east-1)."),
):
    """
    List IAM roles with a specified managed policy attached.
    """
    try:
        iam_client = get_iam_client(profile, region)
        policy_arn = get_policy_arn(iam_client, managed_policy_name)
        logger.info(f"Managed policy ARN: {policy_arn}")

        roles_with_policy = list_roles_with_policy(iam_client, policy_arn, role_regex)
        logger.info(f"\nFound {len(roles_with_policy)} roles with the managed policy '{managed_policy_name}':\n")

        if not roles_with_policy:
            logger.info("No roles found.")
            sys.exit(0)

        # Prepare table data
        table_data = []
        for role_name in roles_with_policy:
            inline_length, inline_count = get_inline_policies(iam_client, role_name)
            managed_policy_count = get_managed_policy_count(iam_client, role_name)
            inline_usage = f"{inline_length} / {INLINE_POLICY_SIZE_LIMIT}"
            managed_policy_usage = f"{managed_policy_count} / {MANAGED_POLICY_LIMIT}"

            table_data.append([
                role_name,
                inline_count,
                inline_usage,
                managed_policy_usage,
            ])

        headers = ["Role Name", "Inline Policy Count", "Inline Policy Size", "Managed Policy Count"]

        logger.info(tabulate(table_data, headers=headers, tablefmt="pretty"))

    except ClientError as e:
        logger.error(f"AWS ClientError: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    app()
