#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script: get_role_policy_info.py
Description: This script returns a list of inline policies attached to an IAM role along with their character lengths,
             the total character length of all inline policies, and a list of managed policies attached to the role
             along with the count.

Usage:
    python get_role_policy_info.py <role_name> [--profile PROFILE] [--region REGION]

Arguments:
    role_name       The name of the IAM role to inspect.

Options:
    --profile PROFILE   The AWS profile to use (default: default).
    --region REGION     The AWS region to use (default: us-east-1).

Requirements:
    - boto3
    - argparse
    - logging
"""

__author__ = "Bradley Kovaluk"
__version__ = "1.0"
__date__ = "2024-09-25" 

import boto3
import argparse
import logging
import sys
import json

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
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

def get_role(iam_client, role_name):
    """
    Get the specified role.

    Args:
        iam_client (boto3.client): The IAM client.
        role_name (str): The name of the IAM role.

    Returns:
        dict: The role if it exists, or None if it doesn't.
    """
    try:
        return iam_client.get_role(RoleName=role_name)['Role']
    except iam_client.exceptions.NoSuchEntityException:
        return None

def get_inline_policies(iam_client, role_name):
    """
    Get inline policies attached to the role along with their character lengths.

    Args:
        iam_client (boto3.client): The IAM client.
        role_name (str): The name of the IAM role.

    Returns:
        tuple: A list of tuples containing policy names and their character lengths, and the total length.
    """
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

def get_managed_policies(iam_client, role_name):
    """
    Get the managed policies attached to the role.

    Args:
        iam_client (boto3.client): The IAM client.
        role_name (str): The name of the IAM role.

    Returns:
        list: A list of managed policy names.
    """
    policies = []
    paginator = iam_client.get_paginator('list_attached_role_policies')
    for page in paginator.paginate(RoleName=role_name):
        for policy in page['AttachedPolicies']:
            policies.append(policy['PolicyName'])
    return policies

def main(role_name, profile='default', region='us-east-1'):
    """
    Main function to get role policy information.

    Args:
        role_name (str): The name of the IAM role to inspect.
        profile (str): The AWS profile to use.
        region (str): The AWS region to use.
    """
    try:
        iam_client = get_iam_client(profile, region)

        role = get_role(iam_client, role_name)
        if not role:
            logger.error(f"Role '{role_name}' not found.")
            sys.exit(1)

        inline_policies, total_inline_length = get_inline_policies(iam_client, role_name)
        managed_policies = get_managed_policies(iam_client, role_name)
        managed_policy_count = len(managed_policies)

        # Output
        logger.info(f"Role Name: {role_name}\n")

        logger.info("Inline Policies and their Character Lengths:")
        if inline_policies:
            for policy_name, length in inline_policies:
                logger.info(f"  - {policy_name}: {length} characters")
            logger.info(f"\nTotal Character Length of All Inline Policies: {total_inline_length}\n")
        else:
            logger.info("  No inline policies attached.\n")

        logger.info("Managed Policies Attached:")
        if managed_policies:
            for policy_name in managed_policies:
                logger.info(f"  - {policy_name}")
            logger.info(f"\nTotal Number of Managed Policies Attached: {managed_policy_count}")
        else:
            logger.info("  No managed policies attached.")

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Get IAM role policy information, including inline policies and managed policies.")
    parser.add_argument('role_name', help="The name of the IAM role to inspect.")
    parser.add_argument('--profile', default='default', help="The AWS profile to use (default: default).")
    parser.add_argument('--region', default='us-east-1', help="The AWS region to use (default: us-east-1).")
    args = parser.parse_args()

    main(args.role_name, args.profile, args.region)
