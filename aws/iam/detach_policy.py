#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script: detach_policy.py
Description: This script detaches a managed policy from an IAM role. It accepts either the policy ARN or the policy name.

Usage:
    python detach_policy.py <role_name> <policy_arn_or_name> [--profile PROFILE] [--region REGION]

Arguments:
    role_name         The name of the IAM role to detach the policy from.
    policy_arn_or_name The ARN or name of the managed policy to detach.

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
__date__ = "2024-01-13"

import boto3
import logging
import typer
from typing import Optional
from botocore.exceptions import ClientError

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = typer.Typer(
    help="Detach a managed policy from an IAM role."
)


def get_policy_arn(iam_client, policy_name: str):
    """Retrieve the ARN of a managed policy given its name."""
    paginator = iam_client.get_paginator("list_policies")
    for page in paginator.paginate(Scope="All"):
        for policy in page["Policies"]:
            if policy["PolicyName"] == policy_name:
                return policy["Arn"]
    raise ValueError(f"Policy with name {policy_name} not found")


def detach_policy_from_role(
    role_name: str,
    policy_arn_or_name: str,
    profile_name: str,
    region_name: str = "us-east-1"
):
    """Detach a managed policy from an IAM role."""
    try:
        session = boto3.Session(profile_name=profile_name, region_name=region_name)
        iam_client = session.client("iam")

        # Check if the input is an ARN or a policy name
        if policy_arn_or_name.startswith("arn:aws:iam::"):
            policy_arn = policy_arn_or_name
        else:
            policy_arn = get_policy_arn(iam_client, policy_arn_or_name)
            logger.info(f"Resolved policy name {policy_arn_or_name} to ARN {policy_arn}")

        # Confirmation prompt
        confirmation = typer.confirm(
            f"Are you sure you want to detach the policy '{policy_arn}' from the role '{role_name}'?",
            default=False
        )
        if not confirmation:
            typer.echo("Operation cancelled.")
            raise typer.Exit()

        iam_client.detach_role_policy(RoleName=role_name, PolicyArn=policy_arn)
        logger.info(f"Detached policy {policy_arn} from role {role_name}")

    except ClientError as e:
        logger.error(f"AWS ClientError: {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        logger.error(f"Error: {e}")
        raise typer.Exit(code=1)


@app.command()
def main(
    role_name: str = typer.Argument(
        ..., help="The name of the IAM role to detach the policy from."
    ),
    policy_arn_or_name: str = typer.Argument(
        ..., help="The ARN or name of the managed policy to detach."
    ),
    profile: str = typer.Option(
        "default", "--profile", help="The name of the AWS profile to use (default: default)."
    ),
    region: str = typer.Option(
        "us-east-1", "--region", help="The AWS region name (default: us-east-1)."
    ),
):
    """
    Detach a managed policy from an IAM role.
    """
    detach_policy_from_role(
        role_name=role_name,
        policy_arn_or_name=policy_arn_or_name,
        profile_name=profile,
        region_name=region,
    )


if __name__ == "__main__":
    app()
