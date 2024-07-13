#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script: delete_ecs_task_definitions.py
Description: This script deletes all task definitions associated with a specified ECS task definition family.

Usage:
    python delete_ecs_task_definitions.py <task_family> [--profile PROFILE] [--region REGION]

Arguments:
    task_family The family of the ECS task definitions to delete.

Options:
    --profile PROFILE The name of the AWS profile to use (default: default).
    --region REGION   The AWS region name (default: us-east-1).

Requirements:
    - boto3
    - argparse
    - logging
"""

__author__ = "Bradley Kovaluk"
__version__ = "1.2"
__date__ = "2024-06-21"

import boto3
import argparse
import logging
import time
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_ecs_client(profile, region):
    """
    Get the ECS client using the specified profile and region.

    Args:
        profile (str): The AWS profile to use.
        region (str): The AWS region to use.

    Returns:
        boto3.client: The ECS client.
    """
    session = boto3.Session(profile_name=profile, region_name=region)
    return session.client('ecs')

def list_task_definitions(ecs_client, task_family):
    """
    List all task definitions for the specified task family.

    Args:
        ecs_client (boto3.client): The ECS client.
        task_family (str): The task family to list task definitions for.

    Returns:
        list: A list of task definition ARNs.
    """
    paginator = ecs_client.get_paginator('list_task_definitions')
    task_definitions = []

    for page in paginator.paginate(familyPrefix=task_family):
        task_definitions.extend(page['taskDefinitionArns'])

    return task_definitions

def delete_task_definitions(ecs_client, task_definitions):
    """
    Delete the specified task definitions.

    Args:
        ecs_client (boto3.client): The ECS client.
        task_definitions (list): A list of task definition ARNs to delete.
    """
    for task_definition in task_definitions:
        try:
            ecs_client.deregister_task_definition(taskDefinition=task_definition)
            logger.info(f"Deregistered task definition: {task_definition}")
            ecs_client.delete_task_definitions(taskDefinition=task_definition)
            logger.info(f"Deleted task definition: {task_definition}")
        except ClientError as e:
            if e.response['Error']['Code'] == 'ThrottlingException':
                logger.warning("Rate limit reached, waiting for 15 seconds...")
                time.sleep(15)
                ecs_client.deregister_task_definition(taskDefinition=task_definition)
                logger.info(f"Deregistered task definition: {task_definition}")
                ecs_client.delete_task_definitions(taskDefinition=task_definition)
                logger.info(f"Deleted task definition: {task_definition}")
            else:
                logger.error(f"Failed to delete task definition {task_definition}: {e}")

def main(task_family, profile='default', region='us-east-1'):
    """
    Main function to delete all task definitions associated with the specified task family.

    Args:
        task_family (str): The family of the ECS task definitions to delete.
        profile (str): The AWS profile to use.
        region (str): The AWS region to use.
    """
    try:
        ecs_client = get_ecs_client(profile, region)
        task_definitions = list_task_definitions(ecs_client, task_family)

        if not task_definitions:
            logger.info("No task definitions found to delete.")
            return
        
        logger.info(f"Found {len(task_definitions)} task definitions for family '{task_family}'.")
        list_choice = input("Would you like to list the task definitions? (y/n): ").strip().lower()

        if list_choice == 'y':
            for task_definition in task_definitions:
                print(task_definition)

        confirm = input("Press Enter to delete these task definitions, or 'n' to cancel: ").strip().lower()
        if confirm == 'n':
            logger.info("Operation cancelled by user.")
            return

        delete_task_definitions(ecs_client, task_definitions)

    except Exception as e:
        logger.error(f"Error: {str(e)}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Delete all ECS task definitions for a specified task family.")
    parser.add_argument('task_family', help="The family of the ECS task definitions to delete.")
    parser.add_argument('--profile', default='default', help="The name of the AWS profile to use (default: default).")
    parser.add_argument('--region', default='us-east-1', help="The AWS region name (default: us-east-1).")
    args = parser.parse_args()

    main(args.task_family, args.profile, args.region)
