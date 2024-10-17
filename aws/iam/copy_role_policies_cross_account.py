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
    - typer
    - json
    - logging
"""

__author__ = "Bradley Kovaluk"
__version__ = "1.1"
__date__ = "2024-09-24"

import boto3
import json
import logging
import sys
import typer
from typing import Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = typer.Typer(
    help="Copy IAM roles across AWS accounts, including managed and inline policies with optional replacements."
)


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


def get_role_tags(iam_client, role_name: str):
    """Get the tags attached to the IAM role."""
    try:
        response = iam_client.list_role_tags(RoleName=role_name)
        tags = response.get('Tags', [])
        while 'Marker' in response:
            response = iam_client.list_role_tags(RoleName=role_name, Marker=response['Marker'])
            tags.extend(response.get('Tags', []))
        return tags
    except iam_client.exceptions.NoSuchEntityException:
        return []


def apply_substring_replacements(document: dict, replacements: dict):
    """Apply substring replacements to a JSON document."""
    doc_json = json.dumps(document)
    for old_str, new_str in replacements.items():
        doc_json = doc_json.replace(old_str, new_str)
    return json.loads(doc_json)


def create_role(iam_client, role: dict, replacements: dict, tags: list):
    """Create a new IAM role in the destination account, applying replacements to the trust policy."""
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


def get_attached_managed_policies(iam_client, role_name: str):
    """Get the managed policies attached to the IAM role."""
    policies = []
    paginator = iam_client.get_paginator('list_attached_role_policies')
    for page in paginator.paginate(RoleName=role_name):
        policies.extend(page['AttachedPolicies'])
    return policies


def attach_managed_policies(iam_client, role_name: str, policies: list):
    """Attach managed policies to the IAM role in the destination account."""
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


def get_policy_arn_by_name(iam_client, policy_name: str):
    """Get the ARN of a managed policy by its name in the destination account."""
    paginator = iam_client.get_paginator('list_policies')
    for page in paginator.paginate(Scope='All', OnlyAttached=False):
        for policy in page['Policies']:
            if policy['PolicyName'] == policy_name:
                return policy['Arn']
    return None


def get_inline_policies(iam_client, role_name: str):
    """Get the inline policies attached to the IAM role."""
    policies = {}
    paginator = iam_client.get_paginator('list_role_policies')
    for page in paginator.paginate(RoleName=role_name):
        for policy_name in page['PolicyNames']:
            policy = iam_client.get_role_policy(RoleName=role_name, PolicyName=policy_name)
            policies[policy_name] = policy['PolicyDocument']
    return policies


def attach_inline_policies(iam_client, role_name: str, policies: dict, replacements: dict):
    """Attach inline policies to the IAM role in the destination account, with substring replacements applied."""
    for policy_name, policy_document in policies.items():
        modified_policy = apply_substring_replacements(policy_document, replacements)
        iam_client.put_role_policy(
            RoleName=role_name,
            PolicyName=policy_name,
            PolicyDocument=json.dumps(modified_policy)
        )
        logger.info(f"Attached inline policy '{policy_name}' to role '{role_name}' with replacements applied.")


def parse_replacements(replace_arg: str):
    """Parse the replacements argument, which is a comma-separated list of key=value pairs."""
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


@app.command()
def main(
    source_profile: str = typer.Argument(..., help="The AWS profile of the source account."),
    target_profile: str = typer.Argument(..., help="The AWS profile of the destination account."),
    role_name: str = typer.Argument(..., help="The name of the IAM role to copy."),
    region: str = typer.Option('us-east-1', "--region", help="The AWS region to use (default: us-east-1)."),
    replace: Optional[str] = typer.Option(
        None,
        "--replace",
        help="Comma-separated list of key=value pairs specifying substrings to replace in the trust policy and inline policies.",
    ),
):
    """
    Copy IAM role from one account to another, including managed and inline policies with optional replacements.
    """
    if replace:
        replacements = parse_replacements(replace)
    else:
        replacements = {}

    try:
        source_iam = get_iam_client(source_profile, region)
        target_iam = get_iam_client(target_profile, region)

        # Get the role from the source account
        role = get_role(source_iam, role_name)
        if not role:
            logger.error(f"Role '{role_name}' not found in the source account.")
            raise typer.Exit(code=1)

        # Get the tags from the source role
        tags = get_role_tags(source_iam, role_name)

        # Check if the role exists in the target account, and create it if it doesn't
        target_role = get_role(target_iam, role_name)
        if not target_role:
            target_role = create_role(target_iam, role, replacements, tags)
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
            attach_inline_policies(target_iam, role_name, inline_policies, replacements)
        else:
            logger.info(f"No inline policies attached to role '{role_name}' in the source account.")

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise typer.Exit(code=1)


if __name__ == '__main__':
    app()
