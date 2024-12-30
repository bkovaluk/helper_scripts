#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script: add_statement_to_trust_policy.py
Description:
    This script adds a new statement to an existing IAM role's trust policy.
    It retrieves the current trust policy, appends the new statement, and then
    updates the role with the modified trust policy.

Usage:
    python add_statement_to_trust_policy.py <role_name> [OPTIONS]

Arguments:
    role_name    The name of the IAM role to update.

Options:
    --profile TEXT       The AWS profile to use (default: default).
    --region TEXT        The AWS region to use (default: us-east-1).
    --principal TEXT     The principal ARN or service to add (e.g., 'arn:aws:iam::123456789012:root').
    --action TEXT        The action (usually 'sts:AssumeRole' for trust policy).
    --effect TEXT        The effect of the statement (default: Allow).
    --condition TEXT     Optional JSON string for conditions (e.g., '{"StringEquals": {"sts:ExternalId": "12345"}}').
                         If not provided, no condition is added.

Requirements:
    - boto3
    - typer
    - logging
    - json
"""

__author__ = "Bradley Kovaluk"
__version__ = "1.0"
__date__ = "2024-12-26"

import boto3
import typer
import json
import logging
from typing import Optional
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = typer.Typer(help="Add a statement to an existing IAM role's trust policy.")

def get_iam_client(profile: str, region: str):
    """
    Return a boto3 IAM client for the given profile and region.
    """
    session = boto3.Session(profile_name=profile, region_name=region)
    return session.client("iam")

def get_role_trust_policy(iam_client, role_name: str) -> dict:
    """
    Get and return the trust policy document for the specified IAM role.
    Raises an exception if the role does not exist or cannot be retrieved.
    """
    try:
        response = iam_client.get_role(RoleName=role_name)
        trust_policy = response["Role"]["AssumeRolePolicyDocument"]
        return trust_policy
    except ClientError as e:
        raise Exception(f"Could not retrieve trust policy for role '{role_name}': {str(e)}")

def update_role_trust_policy(iam_client, role_name: str, trust_policy_document: dict):
    """
    Update the specified IAM role's trust policy with the given document.
    """
    try:
        iam_client.update_assume_role_policy(
            RoleName=role_name,
            PolicyDocument=json.dumps(trust_policy_document)
        )
        logger.info(f"Successfully updated trust policy for role '{role_name}'.")
    except ClientError as e:
        raise Exception(f"Error updating trust policy for role '{role_name}': {str(e)}")

@app.command()
def main(
    role_name: str = typer.Argument(..., help="The name of the IAM role to update."),
    profile: str = typer.Option("default", "--profile", help="The AWS profile to use (default: default)."),
    region: str = typer.Option("us-east-1", "--region", help="The AWS region to use (default: us-east-1)."),
    principal: str = typer.Option(
        ...,
        "--principal",
        help="The principal ARN or service to add (e.g., 'arn:aws:iam::123456789012:root' or 'ec2.amazonaws.com')."
    ),
    action: str = typer.Option(
        "sts:AssumeRole",
        "--action",
        help="The action for the trust policy statement (usually 'sts:AssumeRole').",
    ),
    effect: str = typer.Option(
        "Allow",
        "--effect",
        help="The effect of the statement (default: Allow).",
    ),
    condition: Optional[str] = typer.Option(
        None,
        "--condition",
        help="Optional JSON string for conditions (e.g., '{\"StringEquals\": {\"sts:ExternalId\": \"12345\"}}')."
    ),
):
    """
    Add a new statement to an existing IAM role's trust policy.
    """
    try:
        # Initialize the IAM client
        iam_client = get_iam_client(profile, region)

        # Retrieve the current trust policy
        trust_policy = get_role_trust_policy(iam_client, role_name)

        # Build the new statement
        new_statement = {
            "Effect": effect,
            "Principal": {},
            "Action": action,
        }

        # Determine if principal is an ARN or a service
        # If the principal includes a colon after 'iam::', it's likely an ARN
        if principal.endswith(".com") or "." in principal:
            # Treat it as a service principal
            new_statement["Principal"]["Service"] = principal
        elif principal.startswith("arn:aws:iam::"):
            # Treat it as an AWS principal (ARN)
            new_statement["Principal"]["AWS"] = principal
        else:
            # Fallback to the provided string as AWS principal
            new_statement["Principal"]["AWS"] = principal

        # Parse condition if provided
        if condition:
            try:
                condition_dict = json.loads(condition)
                new_statement["Condition"] = condition_dict
            except json.JSONDecodeError as e:
                raise Exception(f"Invalid JSON for condition: {str(e)}")

        # Insert the new statement into the trust policy
        if "Statement" not in trust_policy:
            trust_policy["Statement"] = []

        trust_policy["Statement"].append(new_statement)

        # Update the role with the modified trust policy
        update_role_trust_policy(iam_client, role_name, trust_policy)

        typer.echo(f"Added statement to role '{role_name}' trust policy:\n{json.dumps(new_statement, indent=2)}")

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    app()
