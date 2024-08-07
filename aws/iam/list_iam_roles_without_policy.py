#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script: list_iam_roles_without_policy.py
Description: This script returns a list of IAM roles that match a regex pattern and do not have any of the specified managed or inline policies attached.
             The script takes multiple managed policies (using list-attached-role-policies) and multiple inline policies (via list-role-policies),
             and returns a list of roles that match the regex pattern but do not contain any of the policies passed as arguments.

Usage:
    python list_iam_roles_without_policy.py <role_regex> [--managed-policy MANAGED_POLICY]... [--inline-policy INLINE_POLICY]... [--profile PROFILE] [--region REGION]

Arguments:
    role_regex The regex pattern to match IAM roles.

Options:
    --managed-policy MANAGED_POLICY The name or ARN of a managed policy to check for (can be specified multiple times).
    --inline-policy INLINE_POLICY   The name of an inline policy to check for (can be specified multiple times).
    --profile PROFILE               The name of the AWS profile to use (default: default).
    --region REGION                 The AWS region name (default: us-east-1).

Requirements:
    - boto3
    - argparse
    - re
    - logging
"""

__author__ = "Bradley Kovaluk"
__version__ = "1.0"
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

def get_policy_arn(iam_client, policy_name_or_arn):
    """
    Get the ARN of the specified managed policy, or return the input if it's already an ARN.

    Args:
        iam_client (boto3.client): The IAM client.
        policy_name_or_arn (str): The name or ARN of the managed policy.

    Returns:
        str: The ARN of the managed policy.
    """
    if policy_name_or_arn.startswith("arn:aws:iam::aws:policy/"):
        return policy_name_or_arn

    paginator = iam_client.get_paginator('list_policies')
    for page in paginator.paginate(Scope='All', OnlyAttached=False):
        for policy in page['Policies']:
            if policy['PolicyName'] == policy_name_or_arn:
                return policy['Arn']

    raise ValueError(f"Managed policy '{policy_name_or_arn}' not found.")

def get_iam_roles(iam_client, role_regex):
    """
    Get a list of IAM roles matching the specified regex pattern.

    Args:
        iam_client (boto3.client): The IAM client.
        role_regex (str): The regex pattern to match IAM roles.

    Returns:
        list: A list of IAM role names.
    """
    paginator = iam_client.get_paginator('list_roles')
    roles = []

    pattern = re.compile(role_regex)

    for page in paginator.paginate():
        for role in page['Roles']:
            if pattern.match(role['RoleName']):
                roles.append(role['RoleName'])

    return roles

def role_has_managed_policy(iam_client, role_name, policy_arn):
    """
    Check if the specified IAM role has the given managed policy attached.

    Args:
        iam_client (boto3.client): The IAM client.
        role_name (str): The name of the IAM role.
        policy_arn (str): The ARN of the managed policy.

    Returns:
        bool: True if the role has the managed policy attached, False otherwise.
    """
    paginator = iam_client.get_paginator('list_attached_role_policies')
    for page in paginator.paginate(RoleName=role_name):
        for policy in page['AttachedPolicies']:
            if policy['PolicyArn'] == policy_arn:
                return True
    return False

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

def main(role_regex, managed_policies, inline_policies, profile='default', region='us-east-1'):
    """
    Main function to list IAM roles without the specified managed or inline policies attached.

    Args:
        role_regex (str): The regex pattern to match IAM roles.
        managed_policies (list): A list of managed policy names or ARNs to check for.
        inline_policies (list): A list of inline policy names to check for.
        profile (str): The AWS profile to use.
        region (str): The AWS region to use.
    """
    if not managed_policies and not inline_policies:
        raise ValueError("At least one managed policy or inline policy must be specified.")

    try:
        iam_client = get_iam_client(profile, region)

        managed_policy_arns = [get_policy_arn(iam_client, policy) for policy in managed_policies]
        roles = get_iam_roles(iam_client, role_regex)
        logger.info(f"Found {len(roles)} roles matching regex '{role_regex}'.")

        roles_without_policies = []
        for role in roles:
            has_any_policy = False
            for policy_arn in managed_policy_arns:
                if role_has_managed_policy(iam_client, role, policy_arn):
                    has_any_policy = True
                    break
            if not has_any_policy:
                for inline_policy in inline_policies:
                    if role_has_inline_policy(iam_client, role, inline_policy):
                        has_any_policy = True
                        break
            if not has_any_policy:
                roles_without_policies.append(role)

        logger.info(f"Found {len(roles_without_policies)} roles without any of the specified policies:")
        for role in roles_without_policies:
            logger.info(role)

    except Exception as e:
        logger.error(f"Error: {str(e)}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="List IAM roles without specified managed or inline policies attached.")
    parser.add_argument('role_regex', help="The regex pattern to match IAM roles.")
    parser.add_argument('--managed-policy', action='append', help="The name or ARN of a managed policy to check for (can be specified multiple times).")
    parser.add_argument('--inline-policy', action='append', help="The name of an inline policy to check for (can be specified multiple times).")
    parser.add_argument('--profile', default='default', help="The name of the AWS profile to use (default: default).")
    parser.add_argument('--region', default='us-east-1', help="The AWS region name (default: us-east-1).")
    args = parser.parse_args()

    main(args.role_regex, args.managed_policy if args.managed_policy else [], args.inline_policy if args.inline_policy else [], args.profile, args.region)
