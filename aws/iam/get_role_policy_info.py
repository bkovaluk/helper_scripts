#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script: get_role_policy_info.py
Description: Retrieves inline and managed policies attached to an IAM role,
             displays their details concisely, and checks against AWS IAM limits.

Usage:
    python get_role_policy_info.py <role_name> [--profile PROFILE] [--region REGION]

Arguments:
    role_name       The name of the IAM role to inspect.

Options:
    --profile PROFILE   The AWS profile to use (default: default).
    --region REGION     The AWS region to use (default: us-east-1).

Requirements:
    - boto3
    - typer
    - tabulate
"""

__author__ = "Bradley Kovaluk"
__version__ = "1.2"
__date__ = "2024-09-25"

import boto3
import sys
import json
import typer
from tabulate import tabulate
from botocore.exceptions import ClientError

app = typer.Typer(help="Get IAM role policy information in a concise format.")

def get_aws_client(service_name: str, profile: str, region: str):
    """Get the AWS client for a specified service."""
    session = boto3.Session(profile_name=profile, region_name=region)
    return session.client(service_name)

def get_role(iam_client, role_name: str):
    """Retrieve the specified IAM role."""
    try:
        return iam_client.get_role(RoleName=role_name)['Role']
    except iam_client.exceptions.NoSuchEntityException:
        return None

def get_inline_policies(iam_client, role_name: str):
    """Retrieve inline policies attached to the role."""
    policies = []
    total_length = 0
    paginator = iam_client.get_paginator('list_role_policies')
    for page in paginator.paginate(RoleName=role_name):
        for policy_name in page['PolicyNames']:
            policy = iam_client.get_role_policy(RoleName=role_name, PolicyName=policy_name)
            policy_document = policy['PolicyDocument']
            policy_json = json.dumps(policy_document, separators=(',', ':'))
            length = len(policy_json)
            policies.append({'Name': policy_name, 'Type': 'Inline', 'Size': length})
            total_length += length
    return policies, total_length

def get_managed_policies(iam_client, role_name: str):
    """Retrieve managed policies attached to the role."""
    policies = []
    paginator = iam_client.get_paginator('list_attached_role_policies')
    for page in paginator.paginate(RoleName=role_name):
        for policy in page['AttachedPolicies']:
            policies.append({'Name': policy['PolicyName'], 'Type': 'Managed'})
    return policies

def get_quota(service_quotas_client, service_code: str, quota_code: str):
    """Get the current value of a specific service quota."""
    try:
        response = service_quotas_client.get_service_quota(
            ServiceCode=service_code,
            QuotaCode=quota_code
        )
        return response['Quota']['Value']
    except ClientError:
        return None

@app.command()
def main(
    role_name: str = typer.Argument(..., help="The name of the IAM role to inspect."),
    profile: str = typer.Option('default', help="The AWS profile to use."),
    region: str = typer.Option('us-east-1', help="The AWS region to use.")
):
    """
    Displays concise information about policies attached to an IAM role.
    """
    try:
        # Initialize AWS clients
        iam_client = get_aws_client('iam', profile, region)
        service_quotas_client = get_aws_client('service-quotas', profile, region)

        # Retrieve the IAM role
        role = get_role(iam_client, role_name)
        if not role:
            print(f"Error: Role '{role_name}' not found.")
            sys.exit(1)

        # Get AWS IAM limits from Service Quotas
        inline_policy_size_limit = get_quota(service_quotas_client, 'iam', 'L-15F2AE72') or 10240
        managed_policy_limit = get_quota(service_quotas_client, 'iam', 'L-F55EF660') or 10

        # Retrieve policies
        inline_policies, total_inline_length = get_inline_policies(iam_client, role_name)
        managed_policies = get_managed_policies(iam_client, role_name)
        total_managed_policies = len(managed_policies)

        # Combine policies for display
        all_policies = inline_policies + managed_policies

        # Prepare data for table
        table_data = []
        for policy in all_policies:
            if policy['Type'] == 'Inline':
                table_data.append([policy['Name'], policy['Type'], f"{policy['Size']} bytes"])
            else:
                table_data.append([policy['Name'], policy['Type'], "-"])

        # Output
        print(f"\nIAM Role: {role_name}")
        if table_data:
            print(tabulate(table_data, headers=["Policy Name", "Policy Type", "Size"], tablefmt="pretty"))
        else:
            print("No policies attached to this role.")

        # Display limits and usage
        print("\nPolicy Limits and Usage:")
        print(f"- Inline Policies Size: {total_inline_length} / {int(inline_policy_size_limit)} bytes")
        print(f"- Managed Policies Attached: {total_managed_policies} / {int(managed_policy_limit)}")

        # Check limits
        if total_inline_length >= inline_policy_size_limit:
            print("Warning: Total inline policy size has reached or exceeded the AWS limit!")

        if total_managed_policies >= managed_policy_limit:
            print("Warning: Managed policy count has reached or exceeded the AWS limit!")

    except ClientError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    app()
