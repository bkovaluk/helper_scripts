#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script: attach_policy.py
Description: This script attaches an existing managed policy to an IAM role. It accepts either the policy ARN or the policy name.

Usage:
    python attach_policy.py <role_name> <policy_arn_or_name> [--profile PROFILE] [--region REGION]

Arguments:
    role_name           The name of the IAM role to attach the policy to.
    policy_arn_or_name  The ARN or name of the managed policy to attach.

Options:
    --profile PROFILE   The name of the AWS profile to use (default: default).
    --region REGION     The AWS region name (default: us-east-1).

Requirements:
    - boto3
    - typer
    - logging
"""

__author__ = "Bradley Kovaluk"
__version__ = "1.1"
__date__ = "2024-01-15"

import boto3
import logging
import typer
from typing import Optional

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = typer.Typer(
    help="Attach a managed policy to an IAM role."
)


def get_policy_arn(iam_client, policy_name: str):
    """Retrieve the ARN of a managed policy given its name."""
    paginator = iam_client.get_paginator("list_policies")
    for page in paginator.paginate(Scope="Local"):
        for policy in page["Policies"]:
            if policy["PolicyName"] == policy_name:
                return policy["Arn"]
    raise ValueError(f"Policy with name {policy_name} not found")


def attach_policy_to_role(
    role_name: str,
    policy_arn_or_name: str,
    profile_name: str = "default",
    region_name: str = "us-east-1"
):
    """Attach a managed policy to an IAM role."""
    session = boto3.Session(profile_name=profile_name, region_name=region_name)
    iam_client = session.client("iam")

    # Check if the input is an ARN or a policy name
    if policy_arn_or_name.startswith("arn:aws:iam::"):
        policy_arn = policy_arn_or_name
    else:
        policy_arn = get_policy_arn(iam_client, policy_arn_or_name)
        logger.info(f"Resolved policy name {policy_arn_or_name} to ARN {policy_arn}")

    response = iam_client.attach_role_policy(RoleName=role_name, PolicyArn=policy_arn)
    logger.info(f"Attached policy {policy_arn} to role {role_name}")

    return response


@app.command()
def main(
    role_name: str = typer.Argument(..., help="The name of the IAM role to attach the policy to."),
    policy_arn_or_name: str = typer.Argument(..., help="The ARN or name of the managed policy to attach."),
    profile: str = typer.Option("default", "--profile", help="The name of the AWS profile to use (default: default)."),
    region: str = typer.Option("us-east-1", "--region", help="The AWS region name (default: us-east-1)."),
):
    """
    Attach a managed policy to an IAM role.
    """
    try:
        response = attach_policy_to_role(
            role_name=role_name,
            policy_arn_or_name=policy_arn_or_name,
            profile_name=profile,
            region_name=region,
        )
        typer.echo(response)
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
