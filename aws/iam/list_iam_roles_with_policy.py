#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script: list_iam_roles_with_policy.py
Description: This script returns a list of IAM roles that have a specified managed policy attached.
             The script takes an optional regex pattern for IAM role names and a managed policy name as arguments.

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
__version__ = "1.2"
__date__ = "2024-07-11"

import boto3
import argparse
import logging
import re

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_iam_roles(role_regex=None):
    """
    Get a list of IAM roles matching the specified regex pattern.

    Args:
        role_regex (str): The regex pattern to match IAM roles. If None, all roles are returned.

    Returns:
        list: A list of IAM role names.
    """
    iam_client = boto3.client('iam')
    paginator = iam_client.get_paginator('list_roles')
    roles = []

    pattern = re.compile(role_regex) if role_regex else None

    for page in paginator.paginate():
        for role in page['Roles']:
            if pattern is None or pattern.match(role['RoleName']):
                roles.append(role['RoleName'])

    return roles

def get_attached_policies(role_name):
    """
    Get a list of managed policies attached to the specified IAM role.

    Args:
        role_name (str): The name of the IAM role.

    Returns:
        list: A list of attached managed policy ARNs.
    """
    iam_client = boto3.client('iam')
    paginator = iam_client.get_paginator('list_attached_role_policies')
    policies = []

    for page in paginator.paginate(RoleName=role_name):
        for policy in page['AttachedPolicies']:
            policies.append(policy['PolicyArn'])

    return policies

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

        roles = get_iam_roles(role_regex)
        logger.info(f"Found {len(roles)} roles matching regex '{role_regex}'.")

        roles_with_policy = []

        for role in roles:
            attached_policies = get_attached_policies(role)
            if policy_arn in attached_policies:
                roles_with_policy.append(role)

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
