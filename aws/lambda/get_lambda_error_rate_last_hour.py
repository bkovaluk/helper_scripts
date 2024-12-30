#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script: get_lambda_error_rate_last_hour.py
Description: This script retrieves AWS Lambda functions' error rates over the last hour and sorts them by error rate.

Usage:
    python get_lambda_error_rate_last_hour.py [--profile PROFILE] [--region REGION] [--verbose]

Options:
    --profile PROFILE   The name of the AWS profile to use (default: default).
    --region REGION     The AWS region name (default: us-east-1).
    --verbose           Enable verbose output to see iteration through Lambda functions.

Requirements:
    - boto3
    - typer
    - rich
"""

__author__ = "Bradley Kovaluk"
__version__ = "1.0"
__date__ = "2024-10-25"

import boto3
import typer
import logging
from datetime import datetime, timedelta, timezone
from rich import print
from rich.logging import RichHandler
from rich.console import Console
from rich.table import Table
from typing import Dict


logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True)]
)
logger = logging.getLogger(__name__)
console = Console()

app = typer.Typer(help="Retrieve AWS Lambda functions' error rates over the last hour.")

def get_lambda_error_rate_last_hour(
    lambda_client,
    cloudwatch_client,
    verbose: bool = False
) -> Dict[str, Dict[str, float]]:
    """
    Retrieves Lambda function error rates based on CloudWatch metrics for the last hour.

    Args:
        lambda_client: The AWS Lambda client.
        cloudwatch_client: The AWS CloudWatch client.
        verbose (bool): If True, enables verbose output to track iteration.

    Returns:
        dict: Dictionary with function name as key and error rate and invocation count as values.
    """
    error_rates = {}
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=1)  # Last hour

    paginator = lambda_client.get_paginator("list_functions")
    function_pages = paginator.paginate()

    for page in function_pages:
        for function in page["Functions"]:
            function_name = function["FunctionName"]
            if verbose:
                logger.info(f"Checking function: {function_name}")

            invocations = cloudwatch_client.get_metric_statistics(
                Namespace="AWS/Lambda",
                MetricName="Invocations",
                Dimensions=[{"Name": "FunctionName", "Value": function_name}],
                StartTime=start_time,
                EndTime=end_time,
                Period=300,  # 5 minutes
                Statistics=["Sum"],
            )
            total_invocations = sum(dp["Sum"] for dp in invocations["Datapoints"])

            errors = cloudwatch_client.get_metric_statistics(
                Namespace="AWS/Lambda",
                MetricName="Errors",
                Dimensions=[{"Name": "FunctionName", "Value": function_name}],
                StartTime=start_time,
                EndTime=end_time,
                Period=300,  # 5 minutes
                Statistics=["Sum"],
            )
            total_errors = sum(dp["Sum"] for dp in errors["Datapoints"])

            if total_invocations > 0:
                error_rate = (total_errors / total_invocations) * 100
            else:
                error_rate = 0.0  # No invocations, no errors

            error_rates[function_name] = {
                "ErrorRate": error_rate,
                "Invocations": total_invocations
            }

            if verbose:
                logger.info(f"  - Error Rate: {error_rate:.2f}% ({total_errors}/{total_invocations})")

    return error_rates

@app.command()
def main(
    profile: str = typer.Option("default", "--profile", help="The name of the AWS profile to use."),
    region: str = typer.Option("us-east-1", "--region", help="The AWS region name."),
    verbose: bool = typer.Option(False, "--verbose", help="Enable verbose output to see iteration through Lambda functions.")
):
    """
    Retrieve AWS Lambda functions' error rates over the last hour based on CloudWatch metrics.
    """
    try:
        session = boto3.Session(profile_name=profile, region_name=region)
        lambda_client = session.client("lambda")
        cloudwatch_client = session.client("cloudwatch")

        error_rates = get_lambda_error_rate_last_hour(
            lambda_client=lambda_client,
            cloudwatch_client=cloudwatch_client,
            verbose=verbose
        )

        if not error_rates:
            console.print("[bold green]No Lambda error data available.[/bold green]")
        else:
            table = Table(title="Lambda Functions Sorted by Error Rate (Last Hour)")
            table.add_column("Function Name", style="bold cyan")
            table.add_column("Error Rate (%)", style="red", justify="right")
            table.add_column("Invocations", style="green", justify="right")

            sorted_error_rates = dict(
                sorted(error_rates.items(), key=lambda item: item[1]["ErrorRate"], reverse=True)
            )

            for function_name, data in sorted_error_rates.items():
                table.add_row(
                    function_name,
                    f"{data['ErrorRate']:.2f}%",
                    f"{int(data['Invocations'])}"
                )

            console.print(table)

    except Exception as e:
        logger.error(f"[bold red]Error:[/bold red] {str(e)}")
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()
