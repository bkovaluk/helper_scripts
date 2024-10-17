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
    - typer
    - logging
    - tabulate
"""

__author__ = "Bradley Kovaluk"
__version__ = "1.4"
__date__ = "2024-05-21"

import boto3
import logging
from botocore.exceptions import ClientError, BotoCoreError
from tabulate import tabulate
import typer
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = typer.Typer(
    help="List ACM certificates that contain a specified FQDN and are in a specified status."
)

VALID_STATUSES = [
    'PENDING_VALIDATION',
    'ISSUED',
    'INACTIVE',
    'EXPIRED',
    'VALIDATION_TIMED_OUT',
    'REVOKED',
    'FAILED',
    'ALL',
]


def get_acm_client(profile: str, region: str):
    """
    Get the ACM client using the specified profile and region.
    """
    session = boto3.Session(profile_name=profile, region_name=region)
    return session.client('acm')


def list_certificates(acm_client, status: str):
    """
    List ACM certificates with the specified status.
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


def get_certificate_details(acm_client, certificate_arn: str):
    """
    Get the details of a specific ACM certificate.
    """
    try:
        response = acm_client.describe_certificate(CertificateArn=certificate_arn)
        return response['Certificate']
    except (ClientError, BotoCoreError) as e:
        logger.error(f"Failed to describe certificate {certificate_arn}: {e}")
        return None


def find_certificates_with_fqdn(certificates: list, acm_client, fqdn: str):
    """
    Find certificates that contain the specified FQDN.
    """
    matching_certificates = []

    for cert_summary in certificates:
        cert_details = get_certificate_details(acm_client, cert_summary['CertificateArn'])
        if cert_details:
            domain_name = cert_details.get('DomainName', '')
            alt_names = cert_details.get('SubjectAlternativeNames', [])
            if fqdn in domain_name or fqdn in alt_names:
                matching_certificates.append(cert_details)

    return matching_certificates


@app.command()
def main(
    fqdn: Optional[str] = typer.Argument(
        None, help="The fully qualified domain name (FQDN) to search for in certificates."
    ),
    status: str = typer.Option(
        'ISSUED',
        "--status",
        help="The status of the certificates to list (default: ISSUED).",
        case_sensitive=False,
        show_choices=True,
    ),
    profile: str = typer.Option(
        'default',
        "--profile",
        help="The name of the AWS profile to use (default: default).",
    ),
    region: str = typer.Option(
        'us-east-1',
        "--region",
        help="The AWS region name (default: us-east-1).",
    ),
    log_level: str = typer.Option(
        'INFO',
        "--log-level",
        help="The logging level (default: INFO).",
        case_sensitive=False,
        show_choices=True,
    ),
):
    """
    List ACM certificates that contain a specified FQDN and are in a specified status.
    """
    logging.getLogger().setLevel(log_level.upper())

    if status.upper() not in VALID_STATUSES:
        typer.echo(f"Invalid status '{status}'. Valid statuses are: {', '.join(VALID_STATUSES)}")
        raise typer.Exit(code=1)

    try:
        acm_client = get_acm_client(profile, region)
        certificates = list_certificates(acm_client, status.upper())

        if fqdn:
            matching_certificates = find_certificates_with_fqdn(certificates, acm_client, fqdn)
        else:
            matching_certificates = [
                get_certificate_details(acm_client, cert['CertificateArn']) for cert in certificates
            ]

        matching_certificates = [cert for cert in matching_certificates if cert]

        if not matching_certificates:
            logger.info("No matching certificates found.")
            return

        table = []
        for cert in matching_certificates:
            table.append([
                cert['CertificateArn'],
                cert['DomainName'],
                ", ".join(cert.get('SubjectAlternativeNames', [])),
                cert.get('NotBefore', 'N/A'),
                cert.get('NotAfter', 'N/A')
            ])

        headers = ["Certificate ARN", "Domain Name", "Subject Alternative Names", "Valid From", "Valid To"]
        typer.echo(tabulate(table, headers=headers))

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise typer.Exit(code=1)


if __name__ == '__main__':
    app()
