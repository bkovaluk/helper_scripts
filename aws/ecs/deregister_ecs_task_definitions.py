#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script: deregister_ecs_task_definitions.py
Description: This script deregisters all task definitions associated with a specified ECS task definition family.

Usage:
    python deregister_ecs_task_definitions.py <task_family> [--profile PROFILE] [--region REGION]

Arguments:
    task_family The family of the ECS task definitions to deregister.

Options:
    --profile PROFILE The name of the AWS profile to use (default: default).
    --region REGION   The AWS region name (default: us-east-1).

Requirements:
    - boto3
    - typer
    - logging
"""

__author__ = "Bradley Kovaluk"
__version__ = "1.1"
__date__ = "2024-07-06"

import boto3
import logging
import time
import typer
from botocore.exceptions import ClientError
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = typer.Typer(
    help="Deregister all ECS task definitions for a specified task family."
)


def get_ecs_client(profile: str, region: str):
    """
    Get the ECS client using the specified profile and region.
    """
    session = boto3.Session(profile_name=profile, region_name=region)
    return session.client('ecs')


def list_task_definitions(ecs_client, task_family: str):
    """
    List all task definitions for the specified task family.
    """
    paginator = ecs_client.get_paginator('list_task_definitions')
    task_definitions = []

    for page in paginator.paginate(familyPrefix=task_family):
        task_definitions.extend(page['taskDefinitionArns'])

    return task_definitions


def deregister_task_definitions(ecs_client, task_definitions: list):
    """
    Deregister the specified task definitions.
    """
    for task_definition in task_definitions:
        try:
            ecs_client.deregister_task_definition(taskDefinition=task_definition)
            logger.info(f"Deregistered task definition: {task_definition}")
        except ClientError as e:
            if e.response['Error']['Code'] == 'ThrottlingException':
                logger.warning("Rate limit reached, waiting for 15 seconds...")
                time.sleep(15)
                ecs_client.deregister_task_definition(taskDefinition=task_definition)
                logger.info(f"Deregistered task definition: {task_definition}")
            else:
                logger.error(f"Failed to deregister task definition {task_definition}: {e}")


@app.command()
def main(
    task_family: str = typer.Argument(
        ..., help="The family of the ECS task definitions to deregister."
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
    Deregister all ECS task definitions for a specified task family.
    """
    try:
        ecs_client = get_ecs_client(profile, region)
        task_definitions = list_task_definitions(ecs_client, task_family)

        if not task_definitions:
            logger.info("No task definitions found to deregister.")
            return

        logger.info(
            f"Found {len(task_definitions)} task definitions for family '{task_family}'."
        )
        list_choice = typer.confirm(
            "Would you like to list the task definitions?", default=False
        )

        if list_choice:
            for task_definition in task_definitions:
                typer.echo(task_definition)

        confirm = typer.confirm(
            "Are you sure you want to deregister these task definitions?",
            default=False,
        )
        if not confirm:
            logger.info("Operation cancelled by user.")
            return

        deregister_task_definitions(ecs_client, task_definitions)

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise typer.Exit(code=1)


if __name__ == '__main__':
    app()
