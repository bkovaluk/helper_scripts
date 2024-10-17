#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script: list_attached_policies.py
Description: This script lists all managed policies attached to an IAM role.

Usage:
    python list_attached_policies.py <role_name> [--profile PROFILE] [--region REGION]

Arguments:
    role_name         The name of the IAM role to list attached policies for.

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
__date__ = "2024-01-15"

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

app = typer.Typer(help="List all managed policies attached to an IAM role.")


def list_attached_policies(
    role_name: str,
    profile_name: str,
    region_name: str = "us-east-1"
):
    """List all managed policies attached to an IAM role."""
    try:
        session = boto3.Session(profile_name=profile_name, region_name=region_name)
        iam_client = session.client("iam")

        paginator = iam_client.get_paginator('list_attached_role_policies')
        policies = []
        for page in paginator.paginate(RoleName=role_name):
            policies.extend(page["AttachedPolicies"])

        if not policies:
            logger.info(f"No managed policies attached to role {role_name}.")
        else:
            for policy in policies:
                logger.info(
                    f"Policy ARN: {policy['PolicyArn']} Policy Name: {policy['PolicyName']}"
                )
        return policies

    except ClientError as e:
        logger.error(f"AWS ClientError: {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        logger.error(f"Error: {e}")
        raise typer.Exit(code=1)


@app.command()
def main(
    role_name: str = typer.Argument(
        ..., help="The name of the IAM role to list attached policies for."
    ),
    profile: str = typer.Option(
        "default", "--profile", help="The name of the AWS profile to use (default: default)."
    ),
    region: str = typer.Option(
        "us-east-1", "--region", help="The AWS region name (default: us-east-1)."
    ),
):
    """
    List all managed policies attached to an IAM role.
    """
    policies = list_attached_policies(
        role_name=role_name,
        profile_name=profile,
        region_name=region,
    )

    for policy in policies:
        print(f"Policy ARN: {policy['PolicyArn']} Policy Name: {policy['PolicyName']}")


if __name__ == "__main__":
    app()
