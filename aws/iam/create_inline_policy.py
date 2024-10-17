#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script: create_inline_policy.py
Description: This script creates an AWS IAM inline policy using a Jinja2 template.
             It reads the policy template from a specified file, renders it with
             the AWS account ID and region, and applies it to a specified IAM role.

Usage:
    python create_inline_policy.py <role_name> <policy_name> <policy_template_path> [--profile PROFILE] [--region REGION]

Arguments:
    role_name           The name of the role to add the inline policy to.
    policy_name         The name of the inline policy.
    policy_template_path The path to the Jinja2 template file inside the 'policies' directory.

Options:
    --profile PROFILE   The name of the AWS profile to use (default: default).
    --region REGION     The AWS region name (default: us-east-1).

Requirements:
    - boto3
    - typer
    - jinja2
    - logging
"""

__author__ = "Bradley Kovaluk"
__version__ = "1.1"
__date__ = "2023-02-14"

import boto3
import logging
import typer
from jinja2 import Environment, FileSystemLoader
from typing import Optional
from botocore.exceptions import ClientError

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = typer.Typer(
    help="Create an AWS IAM inline policy using a Jinja2 template."
)


def get_account_id(session):
    """Get AWS account ID using STS."""
    sts_client = session.client("sts")
    identity = sts_client.get_caller_identity()
    return identity["Account"]


def create_inline_policy(
    role_name: str,
    policy_name: str,
    policy_template_path: str,
    profile_name: str,
    region_name: str = "us-east-1",
):
    """Create an inline policy using a Jinja2 template."""
    try:
        # Set up Jinja2 environment and load template
        env = Environment(loader=FileSystemLoader("policies"))
        template = env.get_template(policy_template_path)

        # Set up Boto3 session
        session = boto3.Session(profile_name=profile_name, region_name=region_name)
        logger.info(f"Using AWS profile: {profile_name} in region: {region_name}")

        # Get the AWS account ID
        account_id = get_account_id(session)
        logger.info(f"Retrieved AWS account ID: {account_id}")

        # Render the policy document using the template
        policy_document = template.render(region=region_name, account_id=account_id)

        iam_client = session.client("iam")

        # Create the inline policy
        response = iam_client.put_role_policy(
            RoleName=role_name,
            PolicyName=policy_name,
            PolicyDocument=policy_document,
        )
        logger.info(f"Created inline policy: {policy_name} for role: {role_name}")

        return response

    except ClientError as e:
        logger.error(f"AWS ClientError: {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        logger.error(f"Error: {e}")
        raise typer.Exit(code=1)


@app.command()
def main(
    role_name: str = typer.Argument(
        ..., help="The name of the role to add the inline policy to."
    ),
    policy_name: str = typer.Argument(
        ..., help="The name of the inline policy."
    ),
    policy_template_path: str = typer.Argument(
        ...,
        help="The path to the Jinja2 template file inside the 'policies' directory.",
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
    Create an AWS IAM inline policy using a Jinja2 template.
    """
    create_inline_policy(
        role_name=role_name,
        policy_name=policy_name,
        policy_template_path=policy_template_path,
        profile_name=profile,
        region_name=region,
    )


if __name__ == "__main__":
    app()
