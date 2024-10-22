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
            length = len(policy_json.encode('utf-8'))
            policies.append({'Name': policy_name, 'Type': 'Inline', 'Size': length})
            total_length += length
    return policies, total_length

def get_managed_policies(iam_client, role_name: str):
    """Retrieve managed policies attached to the role, including their sizes."""
    policies = []
    paginator = iam_client.get_paginator('list_attached_role_policies')
    for page in paginator.paginate(RoleName=role_name):
        for policy in page['AttachedPolicies']:
            policy_arn = policy['PolicyArn']
            policy_name = policy['PolicyName']
            # Retrieve the default version of the policy
            policy_info = iam_client.get_policy(PolicyArn=policy_arn)
            default_version_id = policy_info['Policy']['DefaultVersionId']
            policy_version = iam_client.get_policy_version(
                PolicyArn=policy_arn,
                VersionId=default_version_id
            )
            policy_document = policy_version['PolicyVersion']['Document']
            policy_json = json.dumps(policy_document, separators=(',', ':'))
            length = len(policy_json.encode('utf-8'))
            policies.append({'Name': policy_name, 'Type': 'Managed', 'Size': length})
    return policies

def get_iam_quotas(profile: str, region: str):
    """Retrieve IAM quotas by listing IAM service quotas and searching for the desired limits."""
    # Mapping of quota names to internal keys and default values
    desired_quotas = {
        'Maximum inline policy size (B)': ('InlinePolicySizeLimit', 10240),
        'Maximum managed policies attached to an IAM role': ('ManagedPolicyLimit', 10),
        'Maximum managed policy document size (B)': ('ManagedPolicySizeLimit', 6144),
    }
    # Initialize quotas with default values
    quotas = {value[0]: value[1] for value in desired_quotas.values()}
    try:
        # Initialize Service Quotas client
        session = boto3.Session(profile_name=profile, region_name=region)
        service_quotas_client = session.client('service-quotas')
        # List all quotas for IAM service
        response = service_quotas_client.list_service_quotas(ServiceCode='iam')
        # Update quotas with values from AWS
        quotas.update({
            desired_quotas[quota['QuotaName']][0]: quota['Value']
            for quota in response['Quotas']
            if quota['QuotaName'] in desired_quotas
        })
    except ClientError as e:
        print(f"Error retrieving IAM quotas: {e}")
        # Quotas remain with default values if an error occurs
    return quotas

def generate_table_output(role_name, all_policies, total_inline_length, inline_policy_size_limit,
                          total_managed_policies, managed_policy_limit, managed_policy_size_limit):
    """Generate and display the policies table with totals included."""
    # Prepare data for table
    table_data = []
    for policy in all_policies:
        if policy['Type'] == 'Inline':
            size_display = f"{policy['Size']} bytes"
        else:  # Managed policy
            size_display = f"{policy['Size']} / {int(managed_policy_size_limit)} bytes"
        table_data.append([policy['Name'], policy['Type'], size_display])

    # Add separator row
    separator = ["" for _ in range(len(table_data[0]))]
    table_data.append(separator)

    # Add totals row(s)
    table_data.append(['Total Inline Policies Size', '', f"{total_inline_length} / {int(inline_policy_size_limit)} bytes"])
    table_data.append(['Total Managed Policies Attached', '', f"{total_managed_policies} / {int(managed_policy_limit)}"])

    # Output policies table with 'fancy_grid' format to include borders
    print(f"\nIAM Role: {role_name}")
    if table_data:
        print(tabulate(table_data, headers=["Policy Name", "Policy Type", "Size"], tablefmt="fancy_grid", stralign="left"))
    else:
        print("No policies attached to this role.")

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
        # Initialize IAM client
        iam_client = get_aws_client('iam', profile, region)

        # Retrieve the IAM role
        role = get_role(iam_client, role_name)
        if not role:
            print(f"Error: Role '{role_name}' not found.")
            sys.exit(1)

        # Get AWS IAM limits by listing IAM quotas
        iam_quotas = get_iam_quotas(profile, region)
        inline_policy_size_limit = iam_quotas.get('InlinePolicySizeLimit', 10240)  # Default to 10 KB
        managed_policy_limit = iam_quotas.get('ManagedPolicyLimit', 10)  # Default to 10
        managed_policy_size_limit = iam_quotas.get('ManagedPolicySizeLimit', 6144)  # Default to 6 KB

        # Retrieve policies
        inline_policies, total_inline_length = get_inline_policies(iam_client, role_name)
        managed_policies = get_managed_policies(iam_client, role_name)
        total_managed_policies = len(managed_policies)

        # Combine policies for display
        all_policies = inline_policies + managed_policies

        # Generate and display the policies table
        generate_table_output(
            role_name,
            all_policies,
            total_inline_length,
            inline_policy_size_limit,
            total_managed_policies,
            managed_policy_limit,
            managed_policy_size_limit
        )

        # Check limits and display warnings
        if total_inline_length >= inline_policy_size_limit:
            print("\nWarning: Total inline policy size has reached or exceeded the AWS limit!")

        if total_managed_policies >= managed_policy_limit:
            print("\nWarning: Managed policy count has reached or exceeded the AWS limit!")

        # Check individual managed policies against the size limit
        for policy in managed_policies:
            if policy['Size'] >= managed_policy_size_limit:
                print(f"\nWarning: Managed policy '{policy['Name']}' size has reached or exceeded the AWS limit!")

    except ClientError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    app()
    