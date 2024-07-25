#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script: query_athena.py
Description: This script queries AWS Athena using Jinja2 templates for query generation.

Usage:
    python query_athena.py <template_file> <output_location> [--parameters PARAMETERS] [--profile PROFILE] [--region REGION]

Arguments:
    template_file      The path to the Jinja2 template file for the query.
    output_location    The S3 location for query results (e.g., s3://my-bucket/query-results/).

Options:
    --parameters PARAMETERS  A JSON string of parameters to pass to the query template.
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
__date__ = "2024-07-23"

import boto3
import argparse
import logging
import json
from jinja2 import Environment, FileSystemLoader
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_athena_client(profile, region):
    """
    Get the Athena client using the specified profile and region.

    Args:
        profile (str): The AWS profile to use.
        region (str): The AWS region to use.

    Returns:
        boto3.client: The Athena client.
    """
    session = boto3.Session(profile_name=profile, region_name=region)
    return session.client('athena')

def render_query(template_file, parameters):
    """
    Render the query using the Jinja2 template and provided parameters.

    Args:
        template_file (str): The path to the Jinja2 template file.
        parameters (dict): A dictionary of parameters to pass to the template.

    Returns:
        str: The rendered query.
    """
    env = Environment(loader=FileSystemLoader('.'))
    template = env.get_template(template_file)
    return template.render(parameters)

def execute_query(athena_client, query, output_location):
    """
    Execute the Athena query and wait for the results.

    Args:
        athena_client (boto3.client): The Athena client.
        query (str): The SQL query to execute.
        output_location (str): The S3 location for query results.

    Returns:
        dict: The query execution result.
    """
    try:
        response = athena_client.start_query_execution(
            QueryString=query,
            ResultConfiguration={'OutputLocation': output_location}
        )
        query_execution_id = response['QueryExecutionId']
        logger.info(f"Started query execution with ID: {query_execution_id}")

        # Wait for the query to complete
        while True:
            query_status = athena_client.get_query_execution(QueryExecutionId=query_execution_id)['QueryExecution']['Status']['State']
            if query_status in ['SUCCEEDED', 'FAILED', 'CANCELLED']:
                break
            logger.info("Waiting for query to complete...")
            time.sleep(5)

        # Get the query results
        if query_status == 'SUCCEEDED':
            result = athena_client.get_query_results(QueryExecutionId=query_execution_id)
            return result
        else:
            logger.error(f"Query execution failed with status: {query_status}")
            return None

    except ClientError as e:
        logger.error(f"Error executing query: {e}")
        raise

def main(template_file, output_location, parameters=None, profile='default', region='us-east-1'):
    """
    Main function to execute an Athena query using a Jinja2 template.

    Args:
        template_file (str): The path to the Jinja2 template file.
        output_location (str): The S3 location for query results.
        parameters (str, optional): A JSON string of parameters to pass to the query template.
        profile (str): The AWS profile to use.
        region (str): The AWS region to use.
    """
    try:
        athena_client = get_athena_client(profile, region)
        params = json.loads(parameters) if parameters else {}
        query = render_query(template_file, params)
        logger.info(f"Rendered Query: {query}")
        result = execute_query(athena_client, query, output_location)
        if result:
            logger.info("Query execution succeeded. Results:")
            for row in result['ResultSet']['Rows']:
                logger.info(row)
        else:
            logger.error("Query execution failed.")
    except Exception as e:
        logger.error(f"Error: {str(e)}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Execute an Athena query using a Jinja2 template.")
    parser.add_argument('template_file', help="The path to the Jinja2 template file for the query.")
    parser.add_argument('output_location', help="The S3 location for query results (e.g., s3://my-bucket/query-results/).")
    parser.add_argument('--parameters', help="A JSON string of parameters to pass to the query template.")
    parser.add_argument('--profile', default='default', help="The name of the AWS profile to use (default: default).")
    parser.add_argument('--region', default='us-east-1', help="The AWS region name (default: us-east-1).")
    args = parser.parse_args()

    main(args.template_file, args.output_location, args.parameters, args.profile, args.region)
