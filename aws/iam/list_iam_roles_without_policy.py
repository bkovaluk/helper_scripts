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
    - typer
    - re
    - logging
"""

__author__ = "Bradley Kovaluk"
__version__ = "1.1"
__date__ = "2024-07-11"

import boto3
import logging
import re
import sys
import typer
from typing import List, Optional
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = typer.Typer(help="List IAM roles without specified managed or inline policies attached.")

def get_iam_client(profile: str, region: str):
    """
    Get the IAM client using the specified profile and region.
    """
    session = boto3.Session(profile_name=profile, region_name=region)
    return session.client('iam')

def get_policy_arn(iam_client, policy_name_or_arn: str) -> str:
    """
    Get the ARN of the specified managed policy, or return the input if it's already an ARN.
    """
    if policy_name_or_arn.startswith("arn:aws:iam::") or policy_name_or_arn.startswith("arn:aws:iam::aws:policy/"):
        return policy_name_or_arn

    paginator = iam_client.get_paginator('list_policies')
    for page in paginator.paginate(Scope='All', OnlyAttached=False):
        for policy in page['Policies']:
            if policy['PolicyName'] == policy_name_or_arn:
                return policy['Arn']

    raise ValueError(f"Managed policy '{policy_name_or_arn}' not found.")

def get_iam_roles(iam_client, role_regex: str) -> List[str]:
    """
    Get a list of IAM roles matching the specified regex pattern.
    """
    paginator = iam_client.get_paginator('list_roles')
    roles = []

    pattern = re.compile(role_regex)

    for page in paginator.paginate():
        for role in page['Roles']:
            if pattern.match(role['RoleName']):
                roles.append(role['RoleName'])

    return roles

def role_has_managed_policy(iam_client, role_name: str, policy_arn: str) -> bool:
    """
    Check if the specified IAM role has the given managed policy attached.
    """
    paginator = iam_client.get_paginator('list_attached_role_policies')
    for page in paginator.paginate(RoleName=role_name):
        for policy in page['AttachedPolicies']:
            if policy['PolicyArn'] == policy_arn:
                return True
    return False

def role_has_inline_policy(iam_client, role_name: str, inline_policy_name: str) -> bool:
    """
    Check if the specified IAM role has the given inline policy attached.
    """
    paginator = iam_client.get_paginator('list_role_policies')
    for page in paginator.paginate(RoleName=role_name):
        if inline_policy_name in page['PolicyNames']:
            return True
    return False

@app.command()
def main(
    role_regex: str = typer.Argument(..., help="The regex pattern to match IAM roles."),
    managed_policy: Optional[List[str]] = typer.Option(None, "--managed-policy", help="The name or ARN of a managed policy to check for (can be specified multiple times)."),
    inline_policy: Optional[List[str]] = typer.Option(None, "--inline-policy", help="The name of an inline policy to check for (can be specified multiple times)."),
    profile: str = typer.Option('default', help="The name of the AWS profile to use (default: default)."),
    region: str = typer.Option('us-east-1', help="The AWS region name (default: us-east-1)."),
):
    """
    List IAM roles without specified managed or inline policies attached.
    """
    if not managed_policy and not inline_policy:
        logger.error("At least one managed policy or inline policy must be specified.")
        sys.exit(1)

    try:
        iam_client = get_iam_client(profile, region)

        managed_policy_arns = [get_policy_arn(iam_client, policy) for policy in managed_policy] if managed_policy else []
        roles = get_iam_roles(iam_client, role_regex)
        logger.info(f"Found {len(roles)} roles matching regex '{role_regex}'.")

        roles_without_policies = []
        for role in roles:
            has_any_policy = False
            # Check managed policies
            for policy_arn in managed_policy_arns:
                if role_has_managed_policy(iam_client, role, policy_arn):
                    has_any_policy = True
                    break
            # Check inline policies
            if not has_any_policy and inline_policy:
                for inline_policy_name in inline_policy:
                    if role_has_inline_policy(iam_client, role, inline_policy_name):
                        has_any_policy = True
                        break
            if not has_any_policy:
                roles_without_policies.append(role)

        logger.info(f"Found {len(roles_without_policies)} roles without any of the specified policies:")
        for role in roles_without_policies:
            logger.info(role)

    except ClientError as e:
        logger.error(f"AWS ClientError: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    app()
