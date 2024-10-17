#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script: copy_role_policies.py
Description: This script copies the trust policy and attached policies from a source IAM role to a target IAM role.
             If the target role exists, it performs a diff and only adds missing policies.

Usage:
    python copy_role_policies.py <source_role> <target_role> [--profile PROFILE] [--region REGION]

Arguments:
    source_role        The name of the source IAM role.
    target_role        The name of the target IAM role.

Options:
    --profile PROFILE  The name of the AWS profile to use (default: default).
    --region REGION    The AWS region name (default: us-east-1).

Requirements:
    - boto3
    - typer
    - logging
"""

__author__ = "Bradley Kovaluk"
__version__ = "1.1"
__date__ = "2024-06-15"

import boto3
import logging
import json
import typer
from typing import Optional
from botocore.exceptions import ClientError

# Set up logging
logging.basicConfig(
    level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = typer.Typer(
    help="Copy the trust policy and attached policies from a source IAM role to a target IAM role."
)


def get_role_trust_policy(iam_client, role_name: str):
    """Get the trust policy document of an IAM role."""
    try:
        role = iam_client.get_role(RoleName=role_name)
        return role['Role']['AssumeRolePolicyDocument']
    except ClientError as e:
        logger.error(f"Error getting trust policy for role {role_name}: {e}")
        return None


def get_attached_policies(iam_client, role_name: str):
    """Get all policies attached to a role, both inline and managed."""
    inline_policies = iam_client.list_role_policies(RoleName=role_name)[
        'PolicyNames'
    ]
    managed_policies = iam_client.list_attached_role_policies(RoleName=role_name)[
        'AttachedPolicies'
    ]
    return inline_policies, managed_policies


def get_policy_document(iam_client, role_name: str, policy_name: str):
    """Get the document of an inline policy."""
    policy_document = iam_client.get_role_policy(
        RoleName=role_name, PolicyName=policy_name
    )['PolicyDocument']
    return policy_document


def create_role(iam_client, role_name: str, trust_policy: dict):
    """Create a new IAM role with the specified trust policy."""
    try:
        role = iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy)
        )
        logger.info(f"Created IAM role: {role_name}")
    except iam_client.exceptions.MalformedPolicyDocumentException as e:
        logger.error(
            f"Malformed trust policy for role {role_name}. Skipping trust policy creation."
        )
        logger.error(e)
        role = iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(
                {"Version": "2012-10-17", "Statement": []}
            )
        )
        logger.info(
            f"Created IAM role {role_name} without trust policy due to an error."
        )
    except ClientError as e:
        logger.error(f"Error creating role {role_name}: {e}")
        raise
    return role


def attach_policy_to_role(iam_client, role_name: str, policy_arn: str):
    """Attach a managed policy to an IAM role."""
    iam_client.attach_role_policy(RoleName=role_name, PolicyArn=policy_arn)
    logger.info(f"Attached managed policy {policy_arn} to role {role_name}")


def put_inline_policy(
    iam_client, role_name: str, policy_name: str, policy_document: dict
):
    """Create or update an inline policy for an IAM role."""
    iam_client.put_role_policy(
        RoleName=role_name,
        PolicyName=policy_name,
        PolicyDocument=json.dumps(policy_document)
    )
    logger.info(f"Put inline policy {policy_name} for role {role_name}")


def role_exists(iam_client, role_name: str):
    """Check if an IAM role exists."""
    try:
        iam_client.get_role(RoleName=role_name)
        return True
    except iam_client.exceptions.NoSuchEntityException:
        return False


def copy_role_policies(
    source_role: str,
    target_role: str,
    profile_name: str,
    region_name: str = 'us-east-1'
):
    """Copy the trust policy and attached policies from a source IAM role to a target IAM role."""
    session = boto3.Session(profile_name=profile_name, region_name=region_name)
    iam_client = session.client('iam')

    # Get the trust policy and attached policies from the source role
    trust_policy = get_role_trust_policy(iam_client, source_role)
    if not trust_policy:
        logger.error(f"Could not retrieve trust policy for role {source_role}")
        raise typer.Exit(code=1)

    source_inline_policies, source_managed_policies = get_attached_policies(
        iam_client, source_role
    )

    if not role_exists(iam_client, target_role):
        # Create the target role with the source role's trust policy
        create_role(iam_client, target_role, trust_policy)

        # Copy inline policies
        for policy_name in source_inline_policies:
            policy_document = get_policy_document(
                iam_client, source_role, policy_name
            )
            put_inline_policy(
                iam_client, target_role, policy_name, policy_document
            )

        # Attach managed policies
        for managed_policy in source_managed_policies:
            attach_policy_to_role(
                iam_client, target_role, managed_policy['PolicyArn']
            )

    else:
        logger.info(
            f"Role {target_role} already exists, performing diff and adding missing policies..."
        )

        # Get attached policies from the target role
        target_inline_policies, target_managed_policies = get_attached_policies(
            iam_client, target_role
        )
        target_managed_policy_arns = {
            policy['PolicyArn'] for policy in target_managed_policies
        }

        # Copy missing inline policies
        for policy_name in source_inline_policies:
            if policy_name not in target_inline_policies:
                policy_document = get_policy_document(
                    iam_client, source_role, policy_name
                )
                put_inline_policy(
                    iam_client, target_role, policy_name, policy_document
                )

        # Attach missing managed policies
        for managed_policy in source_managed_policies:
            if managed_policy['PolicyArn'] not in target_managed_policy_arns:
                attach_policy_to_role(
                    iam_client, target_role, managed_policy['PolicyArn']
                )


@app.command()
def main(
    source_role: str = typer.Argument(
        ..., help="The name of the source IAM role."
    ),
    target_role: str = typer.Argument(
        ..., help="The name of the target IAM role."
    ),
    profile: str = typer.Option(
        "default",
        "--profile",
        help="The name of the AWS profile to use (default: default).",
    ),
    region: str = typer.Option(
        "us-east-1",
        "--region",
        help="The AWS region name (default: us-east-1).",
    ),
):
    """
    Copy the trust policy and attached policies from a source IAM role to a target IAM role.
    If the target role exists, it performs a diff and only adds missing policies.
    """
    try:
        copy_role_policies(
            source_role=source_role,
            target_role=target_role,
            profile_name=profile,
            region_name=region
        )
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
