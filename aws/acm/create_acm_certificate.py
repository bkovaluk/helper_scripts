#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script: create_acm_certificate.py
Description: This script creates an ACM certificate with a primary FQDN and optional additional names.
             By default, it uses email validation, but the user can specify DNS validation.

Usage:
    python create_acm_certificate.py <primary_fqdn> [--additional-names ADDITIONAL_NAMES] [--validation-method VALIDATION_METHOD] [--profile PROFILE] [--region REGION]

Arguments:
    primary_fqdn       The primary fully qualified domain name (FQDN) for the certificate.

Options:
    --additional-names ADDITIONAL_NAMES Comma-delimited list of additional FQDNs.
    --validation-method VALIDATION_METHOD The validation method to use (dns or email, default: email).
    --profile PROFILE  The name of the AWS profile to use (default: default).
    --region REGION    The AWS region name (default: us-east-1).

Requirements:
    - boto3
    - argparse
    - logging
"""

__author__ = "Bradley Kovaluk"
__version__ = "1.0"
__date__ = "2024-07-13"

import boto3
import argparse
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_acm_client(profile, region):
    """
    Get the ACM client using the specified profile and region.

    Args:
        profile (str): The AWS profile to use.
        region (str): The AWS region to use.

    Returns:
        boto3.client: The ACM client.
    """
    session = boto3.Session(profile_name=profile, region_name=region)
    return session.client('acm')

def create_certificate(acm_client, primary_fqdn, additional_names, validation_method):
    """
    Create an ACM certificate with the specified FQDNs and validation method.

    Args:
        acm_client (boto3.client): The ACM client.
        primary_fqdn (str): The primary fully qualified domain name (FQDN).
        additional_names (list): A list of additional FQDNs.
        validation_method (str): The validation method (email or dns).

    Returns:
        dict: The response from the ACM request_certificate API call.
    """
    response = acm_client.request_certificate(
        DomainName=primary_fqdn,
        SubjectAlternativeNames=additional_names,
        ValidationMethod=validation_method,
    )
    return response

def main(primary_fqdn, additional_names, validation_method, profile='default', region='us-east-1'):
    """
    Main function to create an ACM certificate with the specified FQDNs and validation method.

    Args:
        primary_fqdn (str): The primary fully qualified domain name (FQDN).
        additional_names (str): A comma-delimited list of additional FQDNs.
        validation_method (str): The validation method (email or dns).
        profile (str): The AWS profile to use.
        region (str): The AWS region to use.
    """
    try:
        acm_client = get_acm_client(profile, region)
        additional_names_list = additional_names.split(',') if additional_names else []
        response = create_certificate(acm_client, primary_fqdn, additional_names_list, validation_method)
        logger.info(f"Certificate request initiated. Certificate ARN: {response['CertificateArn']}")

    except Exception as e:
        logger.error(f"Error: {str(e)}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Create an ACM certificate with a primary FQDN and optional additional names.")
    parser.add_argument('primary_fqdn', help="The primary fully qualified domain name (FQDN) for the certificate.")
    parser.add_argument('--additional-names', help="Comma-delimited list of additional FQDNs.")
    parser.add_argument('--validation-method', default='email', choices=['email', 'dns'], help="The validation method to use (dns or email, default: email).")
    parser.add_argument('--profile', default='default', help="The name of the AWS profile to use (default: default).")
    parser.add_argument('--region', default='us-east-1', help="The AWS region name (default: us-east-1).")
    args = parser.parse_args()

    main(args.primary_fqdn, args.additional_names, args.validation_method, args.profile, args.region)
