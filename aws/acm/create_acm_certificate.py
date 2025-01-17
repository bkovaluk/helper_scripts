#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script: create_acm_certificate.py
Description: This script creates an ACM certificate with a primary FQDN and optional additional names.
             By default, it uses email validation, but the user can specify DNS validation.

Usage:
    python create_acm_certificate.py <primary_fqdn> [--additional-names ADDITIONAL_NAMES] [--validation-method VALIDATION_METHOD] [--validation-emails VALIDATION_EMAILS] [--profile PROFILE] [--region REGION]

Arguments:
    primary_fqdn       The primary fully qualified domain name (FQDN) for the certificate.

Options:
    --additional-names ADDITIONAL_NAMES Comma-delimited list of additional FQDNs.
    --validation-method VALIDATION_METHOD The validation method to use (dns or email, default: email).
    --validation-emails VALIDATION_EMAILS Comma-delimited list of email addresses for email validation.
    --profile PROFILE  The name of the AWS profile to use (default: default).
    --region REGION    The AWS region name (default: us-east-1).

Requirements:
    - boto3
    - typer
    - logging
"""

__author__ = "Bradley Kovaluk"
__version__ = "1.2"
__date__ = "2025-01-17"

import boto3
import logging
import typer
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = typer.Typer(
    help="Create an ACM certificate with a primary FQDN and optional additional names."
)

def get_acm_client(profile: str, region: str):
    """
    Get the ACM client using the specified profile and region.
    """
    session = boto3.Session(profile_name=profile, region_name=region)
    return session.client('acm')

def create_certificate(
    acm_client,
    primary_fqdn: str,
    additional_names: list,
    validation_method: str,
    validation_emails: Optional[list] = None
):
    """
    Create an ACM certificate with the specified FQDNs and validation method.
    """
    request_params = {
        'DomainName': primary_fqdn,
        'SubjectAlternativeNames': additional_names,
        'ValidationMethod': validation_method,
    }
    
    if validation_emails and validation_method == 'EMAIL':
        # Apply email validation for primary FQDN and all SANs
        domains_to_validate = [primary_fqdn] + additional_names
        request_params['DomainValidationOptions'] = [
            {
                'DomainName': domain,
                'ValidationDomain': email,
            }
            for domain in domains_to_validate
            for email in validation_emails
        ]

    response = acm_client.request_certificate(**request_params)
    return response

@app.command()
def main(
    primary_fqdn: str = typer.Argument(
        ..., help="The primary fully qualified domain name (FQDN) for the certificate."
    ),
    additional_names: Optional[str] = typer.Option(
        None,
        "--additional-names",
        help="Comma-delimited list of additional FQDNs.",
    ),
    validation_method: str = typer.Option(
        'email',
        "--validation-method",
        help="The validation method to use (dns or email, default: email).",
        case_sensitive=False,
        show_choices=True,
    ),
    validation_emails: Optional[str] = typer.Option(
        None,
        "--validation-emails",
        help="Comma-delimited list of email addresses for email validation.",
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
):
    """
    Create an ACM certificate with a primary FQDN and optional additional names.
    """
    try:
        acm_client = get_acm_client(profile, region)
        additional_names_list = (
            [name.strip() for name in additional_names.split(',')]
            if additional_names
            else []
        )
        validation_emails_list = (
            [email.strip() for email in validation_emails.split(',')]
            if validation_emails
            else []
        )
        validation_method = validation_method.lower()
        if validation_method not in ['email', 'dns']:
            typer.echo("Validation method must be 'email' or 'dns'.")
            raise typer.Exit(code=1)
        response = create_certificate(
            acm_client, primary_fqdn, additional_names_list, validation_method.upper(), validation_emails_list
        )
        logger.info(
            f"Certificate request initiated. Certificate ARN: {response['CertificateArn']}"
        )
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise typer.Exit(code=1)

if __name__ == '__main__':
    app()
