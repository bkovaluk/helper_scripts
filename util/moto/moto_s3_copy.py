#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script: moto_s3_copy.py
Description: This script simulates copying files between AWS S3 buckets for a set duration. It uses a mock S3 environment (Moto3) to generate realistic S3 paths and simulates file transfers with rich output.

Usage:
    python moto_s3_copy.py --source-bucket <source_bucket_name> --destination-bucket <destination_bucket_name> --run-time <minutes>

Arguments:
    source_bucket       The name of the mock S3 source bucket.
    destination_bucket  The name of the mock S3 destination bucket.
    run_time            The duration (in minutes) for which the script should run, simulating file copies.

Options:
    --source-bucket <source_bucket_name>       Specify a source bucket name for the mock S3 environment (default: "my-source-bucket").
    --destination-bucket <destination_bucket_name>  Specify a destination bucket name (default: "my-destination-bucket").
    --run-time <minutes>                       Set the duration in minutes to simulate the copying process (default: 1).

Requirements:
    - boto3
    - moto
    - typer
    - rich
"""

__author__ = "Bradley Kovaluk"
__version__ = "1.0"
__date__ = "2024-10-25"

import time
import random
import boto3
import uuid
from datetime import datetime, timedelta
from moto import mock_aws
from rich.console import Console
from rich.progress import track
import typer

# Initialize Typer and Rich Console
app = typer.Typer()
console = Console()

# Common variables for generating realistic S3 paths
FOLDERS = [
    "documents", "projects", "images", "backups", "media", "reports", "logs", "configs", "data", "archives"
]
FILE_NAMES = [
    "invoice", "report", "summary", "data", "image", "backup", "config", "log", "document", "media"
]
FILE_EXTENSIONS = [".txt", ".csv", ".pdf", ".log", ".json", ".xml", ".jpg", ".png", ".zip"]

@mock_aws
def setup_mock_s3(bucket_name):
    """
    Sets up a mock S3 environment and creates a mock bucket.

    Args:
        bucket_name (str): The name of the mock bucket to create.

    Returns:
        boto3.resource: The S3 resource used to interact with the mock environment.
    """
    s3 = boto3.resource("s3", region_name="us-east-1")
    s3.create_bucket(Bucket=bucket_name)
    return s3

def generate_moto_s3_path():
    """
    Generates a realistic S3 path using common folder and file names.

    Returns:
        str: A string representing a realistic S3 file path.
    """
    folder_path = "/".join(random.choices(FOLDERS, k=random.randint(1, 3)))
    file_name = f"{random.choice(FILE_NAMES)}_{uuid.uuid4().hex[:8]}{random.choice(FILE_EXTENSIONS)}"
    return f"{folder_path}/{file_name}"

def simulate_copy_process(source_bucket: str, destination_bucket: str, run_time: int):
    """
    Simulates copying files between source and destination buckets for the specified duration.

    Args:
        source_bucket (str): The name of the source S3 bucket.
        destination_bucket (str): The name of the destination S3 bucket.
        run_time (int): The duration (in minutes) to run the simulation.
    """
    s3 = setup_mock_s3(source_bucket)
    setup_mock_s3(destination_bucket)
    console.print(f"[bold blue]Setting up mock S3 buckets:[/bold blue] {source_bucket} -> {destination_bucket}")
    end_time = datetime.now() + timedelta(minutes=run_time)

    while datetime.now() < end_time:
        source_file = generate_moto_s3_path()
        destination = f"s3://{destination_bucket}/{source_file}"
        file_size = random.randint(100, 10240)  # Size in KB

        console.print(f"[bold green]Copying:[/bold green] s3://{source_bucket}/{source_file} -> {destination}")
        time.sleep(random.uniform(0.5, 1.5))  # Simulate copy time
        console.print(f"[italic]File size:[/italic] {file_size} KB")
        console.print(f"[bold cyan]Completed copy of[/bold cyan] {source_file}\n", style="dim")
        time.sleep(random.uniform(0.2, 0.6))  # Delay before the next file

@app.command()
def moto_s3_copy(source_bucket: str = "my-source-bucket", destination_bucket: str = "my-destination-bucket", run_time: int = 1):
    """
    Main function to initiate the S3 file copy simulation.

    Args:
        source_bucket (str): The name of the mock S3 source bucket (default: "my-source-bucket").
        destination_bucket (str): The name of the mock S3 destination bucket (default: "my-destination-bucket").
        run_time (int): Duration in minutes to run the simulation (default: 1).
    """
    console.print("[bold blue]Moto S3 Copy Script Started[/bold blue]\n")
    simulate_copy_process(source_bucket, destination_bucket, run_time)
    console.print("\n[bold green]Moto S3 Copy Script Completed[/bold green]")

if __name__ == "__main__":
    app()
