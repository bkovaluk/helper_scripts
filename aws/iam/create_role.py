#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script: create_role.py
Description: This script creates an AWS IAM role using a Jinja2 template for the trust policy.
             It reads the trust policy template from a specified file, renders it with
             the AWS account ID and region, and creates the role in AWS IAM, including optional tags.

Usage:
    python create_role.py <role_name> <trust_policy_template_path> [--profile PROFILE] [--region REGION] [--description DESCRIPTION] [--tag Key=Value]

Arguments:
    role_name                The name of the IAM role to create.
    trust_policy_template_path The relative path to the Jinja2 template file for the trust policy.

Options:
    --profile PROFILE        The name of the AWS profile to use (default: default).
    --region REGION          The AWS region name (default: us-east-1).
    --description DESCRIPTION The description of the role (default: None).
    --tag Key=Value          Tags to associate with the role (can be specified multiple times).

Requirements:
    - boto3
    - typer
    - jinja2
    - logging
"""

__author__ = "Bradley Kovaluk"
__version__ = "1.3"
__date__ = "2023-04-21"

import boto3
import logging
import os
import typer
from jinja2 import Environment, FileSystemLoader
from typing import Optional, List
from botocore.exceptions import ClientError

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = typer.Typer(
    help="Create an AWS IAM role using a Jinja2 template for the trust policy."
)


def get_account_id(session):
    """Get AWS account ID using STS."""
    sts_client = session.client("sts")
    identity = sts_client.get_caller_identity()
    return identity["Account"]


def parse_tags(tag_list: List[str]):
    """Parse a list of tag strings in the format Key=Value into a list of dictionaries."""
    tags = []
    for tag in tag_list:
        if '=' not in tag:
            logger.error(f"Invalid tag format '{tag}'. Expected format Key=Value.")
            continue
        key, value = tag.split('=', 1)
        tags.append({'Key': key.strip(), 'Value': value.strip()})
    return tags


def create_role(
    role_name: str,
    trust_policy_template_path: str,
    profile_name: str,
    region_name: str = "us-east-1",
    description: Optional[str] = None,
    tags: Optional[List[dict]] = None,
):
    """Create a role using a Jinja2 template for the trust policy."""
    try:
        # Get the directory and filename from the template path
        template_dir = os.path.dirname(trust_policy_template_path) or '.'
        template_filename = os.path.basename(trust_policy_template_path)

        # Set up Jinja2 environment and load template
        env = Environment(loader=FileSystemLoader(template_dir))
        template = env.get_template(template_filename)

        # Set up Boto3 session
        session = boto3.Session(profile_name=profile_name, region_name=region_name)
        logger.info(f"Using AWS profile: {profile_name} in region: {region_name}")

        # Get the AWS account ID
        account_id = get_account_id(session)
        logger.info(f"Retrieved AWS account ID: {account_id}")

        # Render the trust policy document using the template
        trust_policy_document = template.render(
            region=region_name,
            account_id=account_id,
        )

        iam_client = session.client("iam")

        # Create the role
        params = {
            'RoleName': role_name,
            'AssumeRolePolicyDocument': trust_policy_document,
        }
        if description:
            params['Description'] = description
        if tags:
            params['Tags'] = tags

        response = iam_client.create_role(**params)
        logger.info(f"Created role: {role_name}")

        return response

    except ClientError as e:
        logger.error(f"AWS ClientError: {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        logger.error(f"Error: {e}")
        raise typer.Exit(code=1)


@app.command()
def main(
    role_name: str = typer.Argument(..., help="The name of the IAM role to create."),
    trust_policy_template_path: str = typer.Argument(
        ..., help="The relative path to the Jinja2 template file for the trust policy."
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
    description: Optional[str] = typer.Option(
        None, "--description", help="The description of the role."
    ),
    tag: Optional[List[str]] = typer.Option(
        None,
        "--tag",
        help="Tags to associate with the role in the format Key=Value (can be specified multiple times).",
    ),
):
    """
    Create an AWS IAM role using a Jinja2 template for the trust policy.
    """
    tags = []
    if tag:
        tags = parse_tags(tag)

    create_role(
        role_name=role_name,
        trust_policy_template_path=trust_policy_template_path,
        profile_name=profile,
        region_name=region,
        description=description,
        tags=tags,
    )


if __name__ == "__main__":
    app()
