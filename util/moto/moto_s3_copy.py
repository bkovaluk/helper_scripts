#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script: moto_s3_copy.py
Description: This script simulates copying files within an AWS S3 bucket for a set duration. It uses a mock S3 environment (Moto3) to generate fake S3 paths and simulates file transfers with realistic output.

Usage:
    python moto_s3_copy.py --bucket-name <bucket_name> --run-time <minutes>

Arguments:
    bucket_name   The name of the mock S3 bucket to simulate copies within.
    run_time      The duration (in minutes) for which the script should run, simulating file copies.

Options:
    --bucket-name <bucket_name>   Specify a bucket name for the mock S3 environment (default: "my-mock-bucket").
    --run-time <minutes>          Set the duration in minutes to simulate the copying process (default: 1).

Requirements:
    - boto3
    - moto3
    - typer
    - rich
"""

__author__ = "Bradley Kovaluk"
__version__ = "1.2"
__date__ = "2024-09-25"

import time
import random
import boto3
from datetime import datetime, timedelta
from moto import mock_s3
from rich.console import Console
from rich.progress import track
import typer


app = typer.Typer()
console = Console()

# Common variables for generating fake S3 paths
FOLDERS = [
    "documents", "projects", "images", "backups", "media", "reports", "logs", "configs", "data", "archives"
]
FILE_NAMES = [
    "invoice", "report", "summary", "data", "image", "backup", "config", "log", "document", "media"
]
FILE_EXTENSIONS = [".txt", ".csv", ".pdf", ".log", ".json", ".xml", ".jpg", ".png", ".zip"]

@mock_s3
def setup_mock_s3(bucket_name):
    """
    Sets up a mock S3 environment and populates it with a fake bucket.

    Args:
        bucket_name (str): The name of the mock bucket to create.

    Returns:
        tuple: The S3 resource and the created bucket.
    """
    s3 = boto3.resource("s3", region_name="us-east-1")
    bucket = s3.create_bucket(Bucket=bucket_name)
    return s3, bucket

def generate_fake_s3_path():
    """
    Generates a realistic-looking S3 path using common folder and file names.

    Returns:
        str: A string representing a realistic S3 file path.
    """
    folder_path = "/".join(random.choices(FOLDERS, k=random.randint(1, 3)))
    file_name = f"{random.choice(FILE_NAMES)}_{random.randint(100, 999)}{random.choice(FILE_EXTENSIONS)}"
    return f"{folder_path}/{file_name}"

def simulate_copy_process(bucket_name: str, run_time: int):
    """
    Simulates copying files within the mock S3 for the specified duration.

    Args:
        bucket_name (str): The name of the mock S3 bucket to simulate copies in.
        run_time (int): The duration (in minutes) to run the simulation.
    """
    s3, bucket = setup_mock_s3(bucket_name)
    console.print(f"[bold blue]Setting up mock S3 bucket:[/bold blue] {bucket_name}")
    end_time = datetime.now() + timedelta(minutes=run_time)

    while datetime.now() < end_time:
        source_file = generate_fake_s3_path()
        destination = f"s3://{bucket_name}/copy/{source_file}"
        file_size = random.randint(100, 10240)  # Size in KB

        console.print(f"[bold green]Copying:[/bold green] s3://{bucket_name}/{source_file} -> {destination}")
        time.sleep(random.uniform(0.5, 1.5))  # Simulate copy time
        console.print(f"[italic]File size:[/italic] {file_size} KB")
        console.print(f"[bold cyan]Completed copy of[/bold cyan] {source_file}\n", style="dim")
        time.sleep(random.uniform(0.2, 0.6))  # Delay before the next file

@app.command()
def fake_s3_copy(bucket_name: str = "my-mock-bucket", run_time: int = 1):
    """
    Main function to initiate the S3 file copy simulation.

    Args:
        bucket_name (str): The name of the mock S3 bucket (default: "my-mock-bucket").
        run_time (int): Duration in minutes to run the simulation (default: 1).
    """
    console.print("[bold blue]Fake S3 Copy Script Started[/bold blue]\n")
    simulate_copy_process(bucket_name, run_time)
    console.print("\n[bold green]Fake S3 Copy Script Completed[/bold green]")

if __name__ == "__main__":
    app()
