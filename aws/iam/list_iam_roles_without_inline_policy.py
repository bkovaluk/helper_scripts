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
    - argparse
    - re
    - logging
"""

__author__ = "Bradley Kovaluk"
__version__ = "1.5"
__date__ = "2024-07-11"

import boto3
import argparse
import logging
import re

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_iam_client(profile, region):
    """
    Get the IAM client using the specified profile and region.

    Args:
        profile (str): The AWS profile to use.
        region (str): The AWS region to use.

    Returns:
        boto3.client: The IAM client.
    """
    session = boto3.Session(profile_name=profile, region_name=region)
    return session.client('iam')

def get_iam_roles(iam_client, role_regex=None):
    """
    Get a list of IAM roles matching the specified regex pattern.

    Args:
        iam_client (boto3.client): The IAM client.
        role_regex (str): The regex pattern to match IAM roles. If None, all roles are returned.

    Returns:
        list: A list of IAM role names.
    """
    paginator = iam_client.get_paginator('list_roles')
    roles = []

    pattern = re.compile(role_regex) if role_regex else None

    for page in paginator.paginate():
        for role in page['Roles']:
            if pattern is None or pattern.match(role['RoleName']):
                roles.append(role['RoleName'])

    return roles

def role_has_inline_policy(iam_client, role_name, inline_policy_name):
    """
    Check if the specified IAM role has the given inline policy attached.

    Args:
        iam_client (boto3.client): The IAM client.
        role_name (str): The name of the IAM role.
        inline_policy_name (str): The name of the inline policy.

    Returns:
        bool: True if the role has the inline policy attached, False otherwise.
    """
    paginator = iam_client.get_paginator('list_role_policies')
    for page in paginator.paginate(RoleName=role_name):
        if inline_policy_name in page['PolicyNames']:
            return True
    return False

def main(inline_policy_name, role_regex=None, profile='default', region='us-east-1'):
    """
    Main function to list IAM roles without the specified inline policy attached.

    Args:
        inline_policy_name (str): The name of the inline policy to check for.
        role_regex (str): The regex pattern to match IAM roles. If None, all roles are checked.
        profile (str): The AWS profile to use.
        region (str): The AWS region to use.
    """
    try:
        iam_client = get_iam_client(profile, region)

        roles = get_iam_roles(iam_client, role_regex)
        logger.info(f"Found {len(roles)} roles matching regex '{role_regex}'.")

        roles_without_policy = [role for role in roles if not role_has_inline_policy(iam_client, role, inline_policy_name)]

        logger.info(f"Found {len(roles_without_policy)} roles without the inline policy '{inline_policy_name}':")
        for role in roles_without_policy:
            logger.info(role)

    except Exception as e:
        logger.error(f"Error: {str(e)}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="List IAM roles without a specified inline policy attached.")
    parser.add_argument('inline_policy_name', help="The name of the inline policy to check for.")
    parser.add_argument('role_regex', nargs='?', default=None, help="The regex pattern to match IAM roles. If not provided, all roles will be checked.")
    parser.add_argument('--profile', default='default', help="The name of the AWS profile to use (default: default).")
    parser.add_argument('--region', default='us-east-1', help="The AWS region name (default: us-east-1).")
    args = parser.parse_args()

    main(args.inline_policy_name, args.role_regex, args.profile, args.region)
