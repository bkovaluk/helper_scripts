#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script: list_iam_roles_with_policy.py
Description: This script returns a list of IAM roles that have a specified managed policy attached.
             The script takes a managed policy name and an optional regex pattern for IAM role names as arguments.

Usage:
    python list_iam_roles_with_policy.py <managed_policy_name> [<role_regex>]

Arguments:
    managed_policy_name The name of the managed policy to check for.
    role_regex          (Optional) The regex pattern to match IAM roles (e.g., ^APP_). If not provided, all roles will be checked.

Requirements:
    - boto3
    - argparse
    - re
    - logging
"""

__author__ = "Bradley Kovaluk"
__version__ = "1.3"
__date__ = "2024-07-11"

import boto3
import argparse
import logging
import re

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_policy_arn(policy_name):
    """
    Get the ARN of the specified managed policy.

    Args:
        policy_name (str): The name of the managed policy.

    Returns:
        str: The ARN of the managed policy.
    """
    iam_client = boto3.client('iam')
    paginator = iam_client.get_paginator('list_policies')
    for page in paginator.paginate(Scope='Local', OnlyAttached=False):
        for policy in page['Policies']:
            if policy['PolicyName'] == policy_name:
                return policy['Arn']

    raise ValueError(f"Managed policy '{policy_name}' not found.")

def list_roles_with_policy(policy_arn, role_regex=None):
    """
    List IAM roles that have the specified managed policy attached.

    Args:
        policy_arn (str): The ARN of the managed policy.
        role_regex (str): The regex pattern to match IAM roles. If None, all roles are checked.

    Returns:
        list: A list of IAM role names that have the managed policy attached.
    """
    iam_client = boto3.client('iam')
    roles_with_policy = []

    paginator = iam_client.get_paginator('list_entities_for_policy')
    pattern = re.compile(role_regex) if role_regex else None

    for page in paginator.paginate(PolicyArn=policy_arn):
        for role in page.get('PolicyRoles', []):
            role_name = role['RoleName']
            if pattern is None or pattern.match(role_name):
                roles_with_policy.append(role_name)

    return roles_with_policy

def main(managed_policy_name, role_regex=None):
    """
    Main function to list IAM roles with the specified managed policy attached.

    Args:
        managed_policy_name (str): The name of the managed policy to check for.
        role_regex (str): The regex pattern to match IAM roles. If None, all roles are checked.
    """
    try:
        policy_arn = get_policy_arn(managed_policy_name)
        logger.info(f"Managed policy ARN: {policy_arn}")

        roles_with_policy = list_roles_with_policy(policy_arn, role_regex)
        logger.info(f"Found {len(roles_with_policy)} roles with the managed policy '{managed_policy_name}':")
        for role in roles_with_policy:
            logger.info(role)

    except Exception as e:
        logger.error(f"Error: {str(e)}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="List IAM roles with a specified managed policy attached.")
    parser.add_argument('managed_policy_name', help="The name of the managed policy to check for.")
    parser.add_argument('role_regex', nargs='?', default=None, help="The regex pattern to match IAM roles. If not provided, all roles will be checked.")
    args = parser.parse_args()

    main(args.managed_policy_name, args.role_regex)
