#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script: list_sqs_queues.py
Description: This script lists all SQS queues containing a specified substring. If no substring is provided,
             it returns a list of all queues. An optional prefix parameter can also be specified.

Usage:
    python list_sqs_queues.py [--substring SUBSTRING] [--prefix PREFIX] [--profile PROFILE] [--region REGION]

Options:
    --substring SUBSTRING The substring to search for within queue names.
    --prefix PREFIX       The prefix for filtering queue names.
    --profile PROFILE     The name of the AWS profile to use (default: default).
    --region REGION       The AWS region name (default: us-east-1).

Requirements:
    - boto3
    - typer
    - logging
"""

__author__ = "Bradley Kovaluk"
__version__ = "1.2"
__date__ = "2024-07-13"

import boto3
import logging
import re
import typer
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = typer.Typer(
    help="List SQS queues containing a specified substring or matching a prefix."
)


def get_sqs_client(profile: str, region: str):
    """
    Get the SQS client using the specified profile and region.
    """
    session = boto3.Session(profile_name=profile, region_name=region)
    return session.client('sqs')


def list_sqs_queues(
    sqs_client, substring: Optional[str] = None, prefix: Optional[str] = None
):
    """
    List SQS queues that contain a specified substring or match a prefix.
    """
    params = {}
    if prefix:
        params['QueueNamePrefix'] = prefix

    response = sqs_client.list_queues(**params)
    queue_urls = response.get('QueueUrls', [])

    if substring:
        queue_urls = [url for url in queue_urls if substring in url]

    return queue_urls


def highlight_substring(
    text: str, substring: str, color_code: str = "\033[93m"
):
    """
    Highlight the substring in the text with the specified color.
    """
    highlighted_text = re.sub(
        f"({re.escape(substring)})", f"{color_code}\\1\033[0m", text
    )
    return highlighted_text


@app.command()
def main(
    substring: Optional[str] = typer.Option(
        None, "--substring", help="The substring to search for within queue names."
    ),
    prefix: Optional[str] = typer.Option(
        None, "--prefix", help="The prefix for filtering queue names."
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
    List SQS queues containing a specified substring or matching a prefix.
    """
    try:
        sqs_client = get_sqs_client(profile, region)
        queues = list_sqs_queues(sqs_client, substring, prefix)
        logger.info(f"Found {len(queues)} queues matching the criteria.")

        for queue in queues:
            if substring:
                queue = highlight_substring(queue, substring)
            typer.echo(queue)

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise typer.Exit(code=1)


if __name__ == '__main__':
    app()
