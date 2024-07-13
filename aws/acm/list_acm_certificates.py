#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script: list_acm_certificates.py
Description: This script lists ACM certificates that contain a specified FQDN and are in a specified status.
             It will list the FQDNs associated with the certificate as well as the certificate ARN.
             If no FQDN is provided, it will list all certificates in the specified status.

Usage:
    python list_acm_certificates.py [<fqdn>] [--status STATUS] [--profile PROFILE] [--region REGION] [--log-level LOG_LEVEL]

Arguments:
    fqdn              (Optional) The fully qualified domain name (FQDN) to search for in certificates.

Options:
    --status STATUS   The status of the certificates to list (default: ISSUED).
                      Valid statuses: PENDING_VALIDATION, ISSUED, INACTIVE, EXPIRED, VALIDATION_TIMED_OUT, REVOKED, FAILED, ALL.
    --profile PROFILE The name of the AWS profile to use (default: default).
    --region REGION   The AWS region name (default: us-east-1).
    --log-level LOG_LEVEL The logging level (default: INFO).

Requirements:
    - boto3
    - argparse
    - logging
    - tabulate
"""

__author__ = "Bradley Kovaluk"
__version__ = "1.3"
__date__ = "2024-05-21"

import boto3
import argparse
import logging
from botocore.exceptions import ClientError, BotoCoreError
from tabulate import tabulate

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

def list_certificates(acm_client, status):
    """
    List ACM certificates with the specified status.

    Args:
        acm_client (boto3.client): The ACM client.
        status (str): The status of the certificates to list.

    Returns:
        list: A list of certificate summaries.
    """
    paginator = acm_client.get_paginator('list_certificates')
    certificates = []

    if status == 'ALL':
        for page in paginator.paginate():
            certificates.extend(page['CertificateSummaryList'])
    else:
        for page in paginator.paginate(CertificateStatuses=[status]):
            certificates.extend(page['CertificateSummaryList'])

    return certificates

def get_certificate_details(acm_client, certificate_arn):
    """
    Get the details of a specific ACM certificate.

    Args:
        acm_client (boto3.client): The ACM client.
        certificate_arn (str): The ARN of the certificate to get details for.

    Returns:
        dict: The details of the ACM certificate.
    """
    try:
        response = acm_client.describe_certificate(CertificateArn=certificate_arn)
        return response['Certificate']
    except ClientError as e:
        logger.error(f"Failed to describe certificate {certificate_arn}: {e}")
        return None
    except BotoCoreError as e:
        logger.error(f"Failed to describe certificate {certificate_arn}: {e}")
        return None

def find_certificates_with_fqdn(certificates, acm_client, fqdn):
    """
    Find certificates that contain the specified FQDN.

    Args:
        certificates (list): A list of certificate summaries.
        acm_client (boto3.client): The ACM client.
        fqdn (str): The FQDN to search for in certificates.

    Returns:
        list: A list of certificates containing the specified FQDN.
    """
    matching_certificates = []

    for cert_summary in certificates:
        cert_details = get_certificate_details(acm_client, cert_summary['CertificateArn'])
        if cert_details and (fqdn in cert_details['DomainName'] or fqdn in cert_details.get('SubjectAlternativeNames', [])):
            matching_certificates.append(cert_details)

    return matching_certificates

def main(fqdn=None, status='ISSUED', profile='default', region='us-east-1', log_level='INFO'):
    """
    Main function to list ACM certificates that contain the specified FQDN and are in the specified status.

    Args:
        fqdn (str): The FQDN to search for in certificates.
        status (str): The status of the certificates to list.
        profile (str): The AWS profile to use.
        region (str): The AWS region to use.
        log_level (str): The logging level to use.
    """
    logging.getLogger().setLevel(log_level.upper())

    try:
        acm_client = get_acm_client(profile, region)
        certificates = list_certificates(acm_client, status)

        if fqdn:
            matching_certificates = find_certificates_with_fqdn(certificates, acm_client, fqdn)
        else:
            matching_certificates = [get_certificate_details(acm_client, cert['CertificateArn']) for cert in certificates]

        if not matching_certificates:
            logger.info("No matching certificates found.")
            return

        table = []
        for cert in matching_certificates:
            if cert:
                table.append([
                    cert['CertificateArn'],
                    cert['DomainName'],
                    ", ".join(cert.get('SubjectAlternativeNames', [])),
                    cert.get('NotBefore', 'N/A'),
                    cert.get('NotAfter', 'N/A')
                ])

        headers = ["Certificate ARN", "Domain Name", "Subject Alternative Names", "Valid From", "Valid To"]
        print(tabulate(table, headers=headers))

    except Exception as e:
        logger.error(f"Error: {str(e)}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="List ACM certificates that contain a specified FQDN and are in a specified status.")
    parser.add_argument('fqdn', nargs='?', help="The fully qualified domain name (FQDN) to search for in certificates.")
    parser.add_argument('--status', default='ISSUED', choices=['PENDING_VALIDATION', 'ISSUED', 'INACTIVE', 'EXPIRED', 'VALIDATION_TIMED_OUT', 'REVOKED', 'FAILED', 'ALL'], help="The status of the certificates to list (default: ISSUED).")
    parser.add_argument('--profile', default='default', help="The name of the AWS profile to use (default: default).")
    parser.add_argument('--region', default='us-east-1', help="The AWS region name (default: us-east-1).")
    parser.add_argument('--log-level', default='INFO', help="The logging level to use (default: INFO).")
    args = parser.parse_args()

    main(args.fqdn, args.status, args.profile, args.region, args.log_level)
