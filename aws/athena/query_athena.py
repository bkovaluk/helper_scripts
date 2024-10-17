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
    - typer
    - jinja2
    - logging
"""

__author__ = "Bradley Kovaluk"
__version__ = "1.1"
__date__ = "2024-07-23"

import boto3
import logging
import json
import time
from jinja2 import Environment, FileSystemLoader
from botocore.exceptions import ClientError
import typer
from typing import Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = typer.Typer(help="Execute an Athena query using a Jinja2 template.")

def get_athena_client(profile: str, region: str):
    """
    Get the Athena client using the specified profile and region.
    """
    session = boto3.Session(profile_name=profile, region_name=region)
    return session.client('athena')

def render_query(template_file: str, parameters: dict):
    """
    Render the query using the Jinja2 template and provided parameters.
    """
    env = Environment(loader=FileSystemLoader('.'))
    template = env.get_template(template_file)
    return template.render(parameters)

def execute_query(athena_client, query: str, output_location: str):
    """
    Execute the Athena query and wait for the results.
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
            query_execution = athena_client.get_query_execution(QueryExecutionId=query_execution_id)
            query_status = query_execution['QueryExecution']['Status']['State']
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

@app.command()
def main(
    template_file: str = typer.Argument(..., help="The path to the Jinja2 template file for the query."),
    output_location: str = typer.Argument(..., help="The S3 location for query results (e.g., s3://my-bucket/query-results/)."),
    parameters: Optional[str] = typer.Option(
        None,
        "--parameters",
        help="A JSON string of parameters to pass to the query template.",
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
    Execute an Athena query using a Jinja2 template.
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
                logger.info(row['Data'])
        else:
            logger.error("Query execution failed.")
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise typer.Exit(code=1)

if __name__ == '__main__':
    app()
