#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script: copy_roles_policies_cross_account.py
Description: This script copies IAM roles across AWS accounts. It creates the role in the destination
             account if it doesn't exist, attaches managed policies (by alias/name), and copies inline
             policies with the ability to replace substrings (like account IDs or environment variables)
             in the inline policies and the trust policy (assume role policy document). It also copies
             the tags from the source role to the destination role.

Usage:
    python copy_roles_cross_account.py <source_profile> <target_profile> <role_name> [--region REGION] [--replace REPLACE_VALUES]

Arguments:
    source_profile  The AWS profile of the source account.
    target_profile  The AWS profile of the destination account.
    role_name       The name of the IAM role to copy.

Options:
    --region REGION            The AWS region to use (default: us-east-1).
    --replace REPLACE_VALUES   Comma-separated list of key=value pairs specifying substrings
                               to replace in the trust policy and inline policies
                               (e.g., 'old_account_id=new_account_id,old_env=new_env').

Requirements:
    - boto3
    - argparse
    - json
    - logging
"""

__author__ = "Bradley Kovaluk"
__version__ = "1.0"
__date__ = "2024-09-24"

import boto3
import argparse
import json
import logging
import sys

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

def get_role_tags(iam_client, role_name):
    """
    Get the tags attached to the IAM role.

    Args:
        iam_client (boto3.client): The IAM client.
        role_name (str): The name of the IAM role.

    Returns:
        list: A list of tags attached to the role.
    """
    try:
        response = iam_client.list_role_tags(RoleName=role_name)
        tags = response.get('Tags', [])
        while 'Marker' in response:
            response = iam_client.list_role_tags(RoleName=role_name, Marker=response['Marker'])
            tags.extend(response.get('Tags', []))
        return tags
    except iam_client.exceptions.NoSuchEntityException:
        return []

def apply_substring_replacements(document, replacements):
    """
    Apply substring replacements to a JSON document.

    Args:
        document (dict): The original JSON document.
        replacements (dict): The dictionary of substrings to replace.

    Returns:
        dict: The modified document with replacements applied.
    """
    doc_json = json.dumps(document)
    for old_str, new_str in replacements.items():
        doc_json = doc_json.replace(old_str, new_str)
    return json.loads(doc_json)

def create_role(iam_client, role, replacements, tags):
    """
    Create a new IAM role in the destination account, applying replacements to the trust policy.

    Args:
        iam_client (boto3.client): The IAM client.
        role (dict): The role details from the source account.
        replacements (dict): Substring replacements to apply to the trust policy.
        tags (list): A list of tags to attach to the role.

    Returns:
        dict: The created role.
    """
    assume_role_policy = role['AssumeRolePolicyDocument']
    assume_role_policy = apply_substring_replacements(assume_role_policy, replacements)
    role_name = role['RoleName']
    description = role.get('Description', '')
    path = role.get('Path', '/')

    params = {
        'RoleName': role_name,
        'AssumeRolePolicyDocument': json.dumps(assume_role_policy),
        'Description': description,
        'Path': path,
    }

    # Include tags if any
    if tags:
        params['Tags'] = tags

    new_role = iam_client.create_role(**params)
    logger.info(f"Created role '{role_name}' in the destination account with tags and replacements applied to the trust policy.")
    return new_role['Role']

def get_attached_managed_policies(iam_client, role_name):
    """
    Get the managed policies attached to the IAM role.

    Args:
        iam_client (boto3.client): The IAM client.
        role_name (str): The name of the IAM role.

    Returns:
        list: A list of managed policy names attached to the role.
    """
    policies = []
    paginator = iam_client.get_paginator('list_attached_role_policies')
    for page in paginator.paginate(RoleName=role_name):
        policies.extend(page['AttachedPolicies'])
    return policies

def attach_managed_policies(iam_client, role_name, policies):
    """
    Attach managed policies to the IAM role in the destination account.

    Args:
        iam_client (boto3.client): The IAM client.
        role_name (str): The name of the IAM role.
        policies (list): A list of managed policies to attach.
    """
    for policy in policies:
        policy_name = policy['PolicyName']
        # Find the policy ARN in the destination account using the policy name
        dest_policy_arn = get_policy_arn_by_name(iam_client, policy_name)
        if dest_policy_arn:
            iam_client.attach_role_policy(
                RoleName=role_name,
                PolicyArn=dest_policy_arn
            )
            logger.info(f"Attached managed policy '{policy_name}' to role '{role_name}'.")
        else:
            logger.warning(f"Managed policy '{policy_name}' not found in the destination account.")

def get_policy_arn_by_name(iam_client, policy_name):
    """
    Get the ARN of a managed policy by its name in the destination account.

    Args:
        iam_client (boto3.client): The IAM client.
        policy_name (str): The name of the managed policy.

    Returns:
        str: The ARN of the managed policy, or None if not found.
    """
    paginator = iam_client.get_paginator('list_policies')
    for page in paginator.paginate(Scope='All', OnlyAttached=False):
        for policy in page['Policies']:
            if policy['PolicyName'] == policy_name:
                return policy['Arn']
    return None

def get_inline_policies(iam_client, role_name):
    """
    Get the inline policies attached to the IAM role.

    Args:
        iam_client (boto3.client): The IAM client.
        role_name (str): The name of the IAM role.

    Returns:
        dict: A dictionary of inline policy names and their documents.
    """
    policies = {}
    paginator = iam_client.get_paginator('list_role_policies')
    for page in paginator.paginate(RoleName=role_name):
        for policy_name in page['PolicyNames']:
            policy = iam_client.get_role_policy(RoleName=role_name, PolicyName=policy_name)
            policies[policy_name] = policy['PolicyDocument']
    return policies

def attach_inline_policies(iam_client, role_name, policies, replacements):
    """
    Attach inline policies to the IAM role in the destination account, with substring replacements applied.

    Args:
        iam_client (boto3.client): The IAM client.
        role_name (str): The name of the IAM role.
        policies (dict): A dictionary of inline policy names and their documents.
        replacements (dict): A dictionary of substrings to replace in the inline policies.
    """
    for policy_name, policy_document in policies.items():
        modified_policy = apply_substring_replacements(policy_document, replacements)
        iam_client.put_role_policy(
            RoleName=role_name,
            PolicyName=policy_name,
            PolicyDocument=json.dumps(modified_policy)
        )
        logger.info(f"Attached inline policy '{policy_name}' to role '{role_name}' with replacements applied.")

def parse_replacements(replace_arg):
    """
    Parse the replacements argument, which is a comma-separated list of key=value pairs.

    Args:
        replace_arg (str): The replacements argument provided by the user.

    Returns:
        dict: A dictionary of replacements.
    """
    replacements = {}
    pairs = replace_arg.split(',')
    for pair in pairs:
        if '=' in pair:
            key, value = pair.split('=', 1)
            replacements[key] = value
        else:
            logger.error(f"Invalid replacement pair '{pair}'. Expected format 'key=value'.")
            sys.exit(1)
    return replacements

def main(source_profile, target_profile, role_name, region='us-east-1', replacements=None):
    """
    Main function to copy IAM role from one account to another.

    Args:
        source_profile (str): The AWS profile of the source account.
        target_profile (str): The AWS profile of the destination account.
        role_name (str): The name of the IAM role to copy.
        region (str): The AWS region to use.
        replacements (dict): A dictionary of substrings to replace in the trust policy and inline policies.
    """
    try:
        source_iam = get_iam_client(source_profile, region)
        target_iam = get_iam_client(target_profile, region)

        # Get the role from the source account
        role = get_role(source_iam, role_name)
        if not role:
            logger.error(f"Role '{role_name}' not found in the source account.")
            return

        # Get the tags from the source role
        tags = get_role_tags(source_iam, role_name)

        # Check if the role exists in the target account, and create it if it doesn't
        target_role = get_role(target_iam, role_name)
        if not target_role:
            target_role = create_role(target_iam, role, replacements if replacements else {}, tags)
        else:
            logger.info(f"Role '{role_name}' already exists in the destination account.")

        # Get and attach managed policies (by alias)
        managed_policies = get_attached_managed_policies(source_iam, role_name)
        if managed_policies:
            attach_managed_policies(target_iam, role_name, managed_policies)
        else:
            logger.info(f"No managed policies attached to role '{role_name}' in the source account.")

        # Get and attach inline policies (with replacements applied)
        inline_policies = get_inline_policies(source_iam, role_name)
        if inline_policies:
            attach_inline_policies(target_iam, role_name, inline_policies, replacements if replacements else {})
        else:
            logger.info(f"No inline policies attached to role '{role_name}' in the source account.")

    except Exception as e:
        logger.error(f"Error: {str(e)}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Copy IAM role cross-account, including managed policies and inline policies with substring replacements.")
    parser.add_argument('source_profile', help="The AWS profile of the source account.")
    parser.add_argument('target_profile', help="The AWS profile of the destination account.")
    parser.add_argument('role_name', help="The name of the IAM role to copy.")
    parser.add_argument('--region', default='us-east-1', help="The AWS region to use (default: us-east-1).")
    parser.add_argument('--replace', help="Comma-separated list of key=value pairs specifying substrings to replace in the trust policy and inline policies.")
    args = parser.parse_args()

    if args.replace:
        replacements = parse_replacements(args.replace)
    else:
        replacements = {}

    main(args.source_profile, args.target_profile, args.role_name, args.region, replacements)
