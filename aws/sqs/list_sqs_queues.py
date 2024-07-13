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
    - argparse
    - logging
"""

__author__ = "Bradley Kovaluk"
__version__ = "1.1"
__date__ = "2024-07-13"

import boto3
import argparse
import logging
import re

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_sqs_client(profile, region):
    """
    Get the SQS client using the specified profile and region.

    Args:
        profile (str): The AWS profile to use.
        region (str): The AWS region to use.

    Returns:
        boto3.client: The SQS client.
    """
    session = boto3.Session(profile_name=profile, region_name=region)
    return session.client('sqs')

def list_sqs_queues(sqs_client, substring=None, prefix=None):
    """
    List SQS queues that contain a specified substring or match a prefix.

    Args:
        sqs_client (boto3.client): The SQS client.
        substring (str): The substring to search for within queue names.
        prefix (str): The prefix for filtering queue names.

    Returns:
        list: A list of matching SQS queue URLs.
    """
    params = {}
    if prefix:
        params['QueueNamePrefix'] = prefix

    response = sqs_client.list_queues(**params)
    queue_urls = response.get('QueueUrls', [])

    if substring:
        queue_urls = [url for url in queue_urls if substring in url]

    return queue_urls

def highlight_substring(text, substring, color_code="\033[93m"):
    """
    Highlight the substring in the text with the specified color.

    Args:
        text (str): The text to highlight.
        substring (str): The substring to highlight.
        color_code (str): The ANSI color code for highlighting.

    Returns:
        str: The text with the highlighted substring.
    """
    highlighted_text = re.sub(f"({re.escape(substring)})", f"{color_code}\\1\033[0m", text)
    return highlighted_text

def main(substring=None, prefix=None, profile='default', region='us-east-1'):
    """
    Main function to list SQS queues containing a specified substring or matching a prefix.

    Args:
        substring (str): The substring to search for within queue names.
        prefix (str): The prefix for filtering queue names.
        profile (str): The AWS profile to use.
        region (str): The AWS region to use.
    """
    try:
        sqs_client = get_sqs_client(profile, region)
        queues = list_sqs_queues(sqs_client, substring, prefix)
        logger.info(f"Found {len(queues)} queues matching the criteria.")

        for queue in queues:
            if substring:
                queue = highlight_substring(queue, substring)
            print(queue)

    except Exception as e:
        logger.error(f"Error: {str(e)}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="List SQS queues containing a specified substring or matching a prefix.")
    parser.add_argument('--substring', help="The substring to search for within queue names.")
    parser.add_argument('--prefix', help="The prefix for filtering queue names.")
    parser.add_argument('--profile', default='default', help="The name of the AWS profile to use (default: default).")
    parser.add_argument('--region', default='us-east-1', help="The AWS region name (default: us-east-1).")
    args = parser.parse_args()

    main(args.substring, args.prefix, args.profile, args.region)
