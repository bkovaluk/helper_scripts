#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script: get_role_policy_info.py
Description: This script returns a list of inline policies attached to an IAM role along with their character lengths,
             the total character length of all inline policies, and a list of managed policies attached to the role
             along with the count. It also displays how close the role is to AWS IAM limits.

Usage:
    python get_role_policy_info.py <role_name> [--profile PROFILE] [--region REGION]

Arguments:
    role_name       The name of the IAM role to inspect.

Options:
    --profile PROFILE   The AWS profile to use (default: default).
    --region REGION     The AWS region to use (default: us-east-1).

Requirements:
    - boto3
    - typer
    - tabulate
    - logging
"""

__author__ = "Bradley Kovaluk"
__version__ = "1.1"
__date__ = "2024-09-25"

import boto3
import logging
import sys
import json
import typer
from tabulate import tabulate
from botocore.exceptions import ClientError
from typing import List, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

app = typer.Typer(help="Get IAM role policy information, including inline and managed policies.")


def get_iam_client(profile: str, region: str):
    """Get the IAM client using the specified profile and region."""
    session = boto3.Session(profile_name=profile, region_name=region)
    return session.client('iam')


def get_role(iam_client, role_name: str):
    """Get the specified role."""
    try:
        return iam_client.get_role(RoleName=role_name)['Role']
    except iam_client.exceptions.NoSuchEntityException:
        return None


def get_inline_policies(iam_client, role_name: str) -> Tuple[List[Tuple[str, int]], int]:
    """Get inline policies attached to the role along with their character lengths."""
    policies = []
    total_length = 0
    paginator = iam_client.get_paginator('list_role_policies')
    for page in paginator.paginate(RoleName=role_name):
        for policy_name in page['PolicyNames']:
            policy = iam_client.get_role_policy(RoleName=role_name, PolicyName=policy_name)
            policy_document = policy['PolicyDocument']
            policy_json = json.dumps(policy_document, separators=(',', ':'))
            length = len(policy_json)
            policies.append((policy_name, length))
            total_length += length
    return policies, total_length


def get_managed_policies(iam_client, role_name: str) -> List[str]:
    """Get the managed policies attached to the role."""
    policies = []
    paginator = iam_client.get_paginator('list_attached_role_policies')
    for page in paginator.paginate(RoleName=role_name):
        for policy in page['AttachedPolicies']:
            policies.append(policy['PolicyName'])
    return policies


@app.command()
def main(
    role_name: str = typer.Argument(..., help="The name of the IAM role to inspect."),
    profile: str = typer.Option('default', help="The AWS profile to use (default: default)."),
    region: str = typer.Option('us-east-1', help="The AWS region to use (default: us-east-1).")
):
    """
    Returns information about inline and managed policies attached to an IAM role.
    """
    try:
        iam_client = get_iam_client(profile, region)

        role = get_role(iam_client, role_name)
        if not role:
            logger.error(f"Role '{role_name}' not found.")
            sys.exit(1)

        # AWS IAM Limits
        INLINE_POLICY_SIZE_LIMIT = 10240  # 10,240 characters
        MANAGED_POLICY_LIMIT = 10  # Maximum number of managed policies per role

        inline_policies, total_inline_length = get_inline_policies(iam_client, role_name)
        managed_policies = get_managed_policies(iam_client, role_name)
        managed_policy_count = len(managed_policies)

        # Output
        logger.info(f"Role Name: {role_name}\n")

        # Inline Policies
        logger.info("Inline Policies and their Character Lengths:")
        if inline_policies:
            inline_table = [[name, length] for name, length in inline_policies]
            logger.info(tabulate(inline_table, headers=["Policy Name", "Characters"], tablefmt="pretty"))
            logger.info(f"\nTotal Character Length of All Inline Policies: {total_inline_length} / {INLINE_POLICY_SIZE_LIMIT}")
            if total_inline_length >= INLINE_POLICY_SIZE_LIMIT:
                logger.warning("Warning: Total inline policy size has reached or exceeded the AWS limit!")
            else:
                remaining_chars = INLINE_POLICY_SIZE_LIMIT - total_inline_length
                logger.info(f"Remaining characters before reaching limit: {remaining_chars}\n")
        else:
            logger.info("  No inline policies attached.\n")

        # Managed Policies
        logger.info("Managed Policies Attached:")
        if managed_policies:
            managed_table = [[name] for name in managed_policies]
            logger.info(tabulate(managed_table, headers=["Policy Name"], tablefmt="pretty"))
            logger.info(f"\nTotal Number of Managed Policies Attached: {managed_policy_count} / {MANAGED_POLICY_LIMIT}")
            if managed_policy_count >= MANAGED_POLICY_LIMIT:
                logger.warning("Warning: Managed policy count has reached or exceeded the AWS limit!")
            else:
                remaining_policies = MANAGED_POLICY_LIMIT - managed_policy_count
                logger.info(f"Remaining managed policies before reaching limit: {remaining_policies}")
        else:
            logger.info("  No managed policies attached.")

    except ClientError as e:
        logger.error(f"AWS ClientError: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    app()
