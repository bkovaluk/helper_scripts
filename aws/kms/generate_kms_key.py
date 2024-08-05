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
    - argparse
    - jinja2
    - logging
"""

__author__ = "Bradley Kovaluk"
__version__ = "1.0"
__date__ = "2024-08-05"

import boto3
import argparse
import logging
import json
from jinja2 import Environment, FileSystemLoader
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_sts_client(profile, region):
    """
    Get the STS client using the specified profile and region.

    Args:
        profile (str): The AWS profile to use.
        region (str): The AWS region to use.

    Returns:
        boto3.client: The STS client.
    """
    session = boto3.Session(profile_name=profile, region_name=region)
    return session.client('sts')

def get_account_id(sts_client):
    """
    Get the AWS account ID using STS.

    Args:
        sts_client (boto3.client): The STS client.

    Returns:
        str: The AWS account ID.
    """
    try:
        identity = sts_client.get_caller_identity()
        return identity['Account']
    except ClientError as e:
        logger.error(f"Error getting account ID: {e}")
        raise

def get_kms_client(profile, region):
    """
    Get the KMS client using the specified profile and region.

    Args:
        profile (str): The AWS profile to use.
        region (str): The AWS region to use.

    Returns:
        boto3.client: The KMS client.
    """
    session = boto3.Session(profile_name=profile, region_name=region)
    return session.client('kms')

def render_policy(template_file, parameters):
    """
    Render the key policy using the Jinja2 template and provided parameters.

    Args:
        template_file (str): The path to the Jinja2 template file.
        parameters (dict): A dictionary of parameters to pass to the template.

    Returns:
        str: The rendered key policy.
    """
    env = Environment(loader=FileSystemLoader('.'))
    template = env.get_template(template_file)
    return template.render(parameters)

def create_kms_key(kms_client, key_policy):
    """
    Create a KMS key with the specified key policy.

    Args:
        kms_client (boto3.client): The KMS client.
        key_policy (str): The key policy to apply.

    Returns:
        dict: The created KMS key details.
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

def enable_key_rotation(kms_client, key_id):
    """
    Enable key rotation for the specified KMS key.

    Args:
        kms_client (boto3.client): The KMS client.
        key_id (str): The ID of the KMS key.
    """
    try:
        kms_client.enable_key_rotation(KeyId=key_id)
        logger.info(f"Enabled key rotation for KMS key with ID: {key_id}")
    except ClientError as e:
        logger.error(f"Error enabling key rotation for KMS key with ID {key_id}: {e}")
        raise

def create_key_alias(kms_client, key_id, alias_name):
    """
    Create an alias for the specified KMS key.

    Args:
        kms_client (boto3.client): The KMS client.
        key_id (str): The ID of the KMS key.
        alias_name (str): The alias name for the KMS key.
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

def parse_parameters(parameters):
    """
    Parse the parameters argument into a dictionary.

    Args:
        parameters (str): The parameters argument as a JSON string or comma-delimited list.

    Returns:
        dict: A dictionary of parameters.
    """
    try:
        return json.loads(parameters)
    except json.JSONDecodeError:
        params = {}
        pairs = parameters.split(',')
        for pair in pairs:
            key, value = pair.split('=')
            params[key.strip()] = value.strip()
        return params

def main(kms_key_alias, template_file, parameters, enable_key_rotation_flag, profile='default', region='us-east-1'):
    """
    Main function to generate a KMS key with a specified key policy and alias.

    Args:
        kms_key_alias (str): The alias name for the KMS key.
        template_file (str): The path to the Jinja2 template file for the key policy.
        parameters (str): A JSON string or a comma-delimited list of parameters to pass to the key policy template.
        enable_key_rotation_flag (bool): Whether to enable key rotation for the created KMS key.
        profile (str): The AWS profile to use.
        region (str): The AWS region to use.
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
            logger.info("KMS key creation succeeded. Key details:")
            logger.info(result)
            create_key_alias(kms_client, result['KeyMetadata']['KeyId'], kms_key_alias)
            if enable_key_rotation_flag:
                enable_key_rotation(kms_client, result['KeyMetadata']['KeyId'])
        else:
            logger.error("KMS key creation failed.")
    except Exception as e:
        logger.error(f"Error: {str(e)}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generate a KMS key with a specified key policy using Jinja2 template and assign an alias.")
    parser.add_argument('kms_key_alias', help="The alias name for the KMS key.")
    parser.add_argument('template_file', help="The path to the Jinja2 template file for the key policy.")
    parser.add_argument('--parameters', help="A JSON string or a comma-delimited list of parameters to pass to the key policy template.")
    parser.add_argument('--enable-key-rotation', action='store_true', help="Enable key rotation for the created KMS key.")
    parser.add_argument('--profile', default='default', help="The name of the AWS profile to use (default: default).")
    parser.add_argument('--region', default='us-east-1', help="The AWS region name (default: us-east-1).")
    args = parser.parse_args()

    main(args.kms_key_alias, args.template_file, args.parameters, args.enable_key_rotation, args.profile, args.region)
