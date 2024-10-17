#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script: generate_kms_key.py
Description: This script generates a KMS key with a specified key policy using Jinja2 for template rendering and assigns a specified alias.

Usage:
    python generate_kms_key.py <kms_key_alias> <template_file> --parameters PARAMETERS [--enable-key-rotation] [--profile PROFILE] [--region REGION]

Arguments:
    kms_key_alias      The alias name for the KMS key.
    template_file      The path to the Jinja2 template file for the key policy.

Options:
    --parameters PARAMETERS  A JSON string or a comma-delimited list of parameters to pass to the key policy template.
    --enable-key-rotation    Enable key rotation for the created KMS key.
    --profile PROFILE        The name of the AWS profile to use (default: default).
    --region REGION          The AWS region name (default: us-east-1).

Requirements:
    - boto3
    - typer
    - jinja2
    - logging
"""

__author__ = "Bradley Kovaluk"
__version__ = "1.1"
__date__ = "2024-08-05"

import boto3
import logging
import json
from jinja2 import Environment, FileSystemLoader
from botocore.exceptions import ClientError
import typer
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = typer.Typer(
    help="Generate a KMS key with a specified key policy using Jinja2 template and assign an alias."
)


def get_sts_client(profile: str, region: str):
    """
    Get the STS client using the specified profile and region.
    """
    session = boto3.Session(profile_name=profile, region_name=region)
    return session.client('sts')


def get_account_id(sts_client):
    """
    Get the AWS account ID using STS.
    """
    try:
        identity = sts_client.get_caller_identity()
        return identity['Account']
    except ClientError as e:
        logger.error(f"Error getting account ID: {e}")
        raise


def get_kms_client(profile: str, region: str):
    """
    Get the KMS client using the specified profile and region.
    """
    session = boto3.Session(profile_name=profile, region_name=region)
    return session.client('kms')


def render_policy(template_file: str, parameters: dict) -> str:
    """
    Render the key policy using the Jinja2 template and provided parameters.
    """
    env = Environment(loader=FileSystemLoader('.'))
    template = env.get_template(template_file)
    return template.render(parameters)


def create_kms_key(kms_client, key_policy: str):
    """
    Create a KMS key with the specified key policy.
    """
    try:
        response = kms_client.create_key(
            Policy=key_policy,
            Description='KMS key created by generate_kms_key.py script'
        )
        key_id = response['KeyMetadata']['KeyId']
        logger.info(f"Created KMS key with ID: {key_id}")
        return response
    except ClientError as e:
        logger.error(f"Error creating KMS key: {e}")
        raise


def enable_key_rotation(kms_client, key_id: str):
    """
    Enable key rotation for the specified KMS key.
    """
    try:
        kms_client.enable_key_rotation(KeyId=key_id)
        logger.info(f"Enabled key rotation for KMS key with ID: {key_id}")
    except ClientError as e:
        logger.error(f"Error enabling key rotation for KMS key with ID {key_id}: {e}")
        raise


def create_key_alias(kms_client, key_id: str, alias_name: str):
    """
    Create an alias for the specified KMS key.
    """
    try:
        kms_client.create_alias(
            AliasName=f'alias/{alias_name}',
            TargetKeyId=key_id
        )
        logger.info(f"Created alias 'alias/{alias_name}' for KMS key with ID: {key_id}")
    except ClientError as e:
        logger.error(f"Error creating alias 'alias/{alias_name}' for KMS key with ID {key_id}: {e}")
        raise


def parse_parameters(parameters: str) -> dict:
    """
    Parse the parameters argument into a dictionary.
    """
    try:
        return json.loads(parameters)
    except json.JSONDecodeError:
        params = {}
        pairs = parameters.split(',')
        for pair in pairs:
            if '=' in pair:
                key, value = pair.split('=', 1)
                params[key.strip()] = value.strip()
            else:
                logger.error(f"Invalid parameter format: {pair}")
                raise ValueError(f"Invalid parameter format: {pair}")
        return params


@app.command()
def main(
    kms_key_alias: str = typer.Argument(..., help="The alias name for the KMS key."),
    template_file: str = typer.Argument(..., help="The path to the Jinja2 template file for the key policy."),
    parameters: Optional[str] = typer.Option(
        None,
        "--parameters",
        help="A JSON string or comma-delimited list of parameters to pass to the key policy template.",
    ),
    enable_key_rotation_flag: bool = typer.Option(
        False,
        "--enable-key-rotation",
        is_flag=True,
        help="Enable key rotation for the created KMS key.",
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
    Generate a KMS key with a specified key policy using Jinja2 template and assign an alias.
    """
    try:
        sts_client = get_sts_client(profile, region)
        account_id = get_account_id(sts_client)
        kms_client = get_kms_client(profile, region)

        params = parse_parameters(parameters) if parameters else {}
        params.setdefault('account_id', account_id)

        key_policy = render_policy(template_file, params)
        logger.info(f"Rendered Key Policy: {key_policy}")
        result = create_kms_key(kms_client, key_policy)
        if result:
            logger.info("KMS key creation succeeded.")
            create_key_alias(kms_client, result['KeyMetadata']['KeyId'], kms_key_alias)
            if enable_key_rotation_flag:
                enable_key_rotation(kms_client, result['KeyMetadata']['KeyId'])
        else:
            logger.error("KMS key creation failed.")
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise typer.Exit(code=1)


if __name__ == '__main__':
    app()
