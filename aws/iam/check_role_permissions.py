#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script: check_role_permissions.py
Description: This script checks if an IAM role has a policy with specific permissions (service, action, and resource).
             It outputs all the policies with the specified permissions and any conditions that must be met.

Usage:
    python check_role_permissions.py <role_name> <service> <action> <resource> [--profile PROFILE] [--region REGION]

Arguments:
    role_name         The name of the IAM role to check.
    service           The service for the permission (e.g., s3).
    action            The action for the permission (e.g., GetObject).
    resource          The resource for the permission (e.g., arn:aws:s3:::example-bucket/*).

Options:
    --profile PROFILE The name of the AWS profile to use (default: default).
    --region REGION   The AWS region name (default: us-east-1).

Requirements:
    - boto3
    - typer
    - logging
"""

__author__ = "Bradley Kovaluk"
__version__ = "1.1"
__date__ = "2024-03-03"

import boto3
import logging
import json
import re
import typer
from typing import Optional

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = typer.Typer(
    help="Check if an IAM role has a policy with specific permissions."
)


def get_attached_policies(iam_client, role_name: str):
    """Get all policies attached to a role, both inline and managed."""
    inline_policies = iam_client.list_role_policies(RoleName=role_name)["PolicyNames"]
    managed_policies = iam_client.list_attached_role_policies(RoleName=role_name)[
        "AttachedPolicies"
    ]
    return inline_policies, managed_policies


def get_policy_document(iam_client, role_name: str, policy_name: str):
    """Get the document of an inline policy."""
    policy_document = iam_client.get_role_policy(
        RoleName=role_name, PolicyName=policy_name
    )["PolicyDocument"]
    return policy_document


def get_managed_policy_document(iam_client, policy_arn: str):
    """Get the document of a managed policy."""
    policy = iam_client.get_policy(PolicyArn=policy_arn)
    policy_version = iam_client.get_policy_version(
        PolicyArn=policy_arn, VersionId=policy["Policy"]["DefaultVersionId"]
    )
    policy_document = policy_version["PolicyVersion"]["Document"]
    return policy_document


def match_resource(resource_pattern: str, resource: str):
    """Check if a resource matches a resource pattern with wildcards."""
    # Escape special characters for regex and replace AWS wildcards
    resource_pattern = re.escape(resource_pattern)
    resource_pattern = resource_pattern.replace(r"\*", ".*").replace(r"\?", ".")
    return re.fullmatch(resource_pattern, resource) is not None


def check_permission(policy_document: dict, service: str, action: str, resource: str):
    """Check if the policy document contains the specified permission."""
    action_full = f"{service}:{action}"
    for statement in policy_document.get("Statement", []):
        if statement["Effect"] != "Allow":
            continue
        actions = statement.get("Action", [])
        if isinstance(actions, str):
            actions = [actions]
        resources = statement.get("Resource", [])
        if isinstance(resources, str):
            resources = [resources]
        if action_full in actions or "*" in actions:
            if any(match_resource(res, resource) or res == "*" for res in resources):
                conditions = statement.get("Condition", None)
                return True, conditions
    return False, None


def check_role_permissions(
    role_name: str,
    service: str,
    action: str,
    resource: str,
    profile_name: str = "default",
    region_name: str = "us-east-1",
):
    """Check if an IAM role has a policy with specific permissions and output the policies with conditions."""
    session = boto3.Session(profile_name=profile_name, region_name=region_name)
    iam_client = session.client("iam")

    inline_policies, managed_policies = get_attached_policies(iam_client, role_name)

    policies_with_permissions = []

    # Check inline policies
    for policy_name in inline_policies:
        policy_document = get_policy_document(iam_client, role_name, policy_name)
        has_permission, conditions = check_permission(
            policy_document, service, action, resource
        )
        if has_permission:
            policies_with_permissions.append(
                {
                    "PolicyType": "Inline",
                    "PolicyName": policy_name,
                    "Conditions": conditions,
                }
            )

    # Check managed policies
    for managed_policy in managed_policies:
        policy_arn = managed_policy["PolicyArn"]
        policy_document = get_managed_policy_document(iam_client, policy_arn)
        has_permission, conditions = check_permission(
            policy_document, service, action, resource
        )
        if has_permission:
            policies_with_permissions.append(
                {
                    "PolicyType": "Managed",
                    "PolicyName": managed_policy["PolicyName"],
                    "PolicyArn": policy_arn,
                    "Conditions": conditions,
                }
            )

    return policies_with_permissions


@app.command()
def main(
    role_name: str = typer.Argument(..., help="The name of the IAM role to check."),
    service: str = typer.Argument(..., help="The service for the permission (e.g., s3)."),
    action: str = typer.Argument(..., help="The action for the permission (e.g., GetObject)."),
    resource: str = typer.Argument(
        ..., help="The resource for the permission (e.g., arn:aws:s3:::example-bucket/*)."
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
    Check if an IAM role has a policy with specific permissions.
    """
    try:
        policies = check_role_permissions(
            role_name=role_name,
            service=service,
            action=action,
            resource=resource,
            profile_name=profile,
            region_name=region,
        )

        if policies:
            logger.info("Found the following policies with the specified permissions:")
            for policy in policies:
                typer.echo(json.dumps(policy, indent=2))
        else:
            logger.info("Permission not found in any attached policy.")
            typer.echo("Permission not found in any attached policy.")

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
