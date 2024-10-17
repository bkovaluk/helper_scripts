#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script: copy_rds_snapshot.py
Description: This script copies an RDS snapshot (cluster or instance) between AWS accounts. It copies the source snapshot
             to the source account using a shared KMS key, shares it with the target account, and then copies it to the
             target account using the target KMS key (if provided).

Usage:
    python copy_rds_snapshot.py <source_snapshot_name> [--target-snapshot-name TARGET_SNAPSHOT_NAME]
                                --shared-kms-key SHARED_KMS_KEY --source-account-id SOURCE_ACCOUNT_ID
                                --target-account-id TARGET_ACCOUNT_ID [--target-kms-key TARGET_KMS_KEY]
                                [--source-profile SOURCE_PROFILE] [--target-profile TARGET_PROFILE]
                                [--source-region SOURCE_REGION] [--target-region TARGET_REGION]

Arguments:
    source_snapshot_name   The name of the source RDS snapshot.

Options:
    --target-snapshot-name TARGET_SNAPSHOT_NAME The name of the target RDS snapshot (optional).
    --shared-kms-key SHARED_KMS_KEY             The shared KMS key ARN.
    --target-kms-key TARGET_KMS_KEY             The target KMS key ARN (optional).
    --source-account-id SOURCE_ACCOUNT_ID       The AWS account ID of the source account.
    --target-account-id TARGET_ACCOUNT_ID       The AWS account ID of the target account.
    --source-profile SOURCE_PROFILE             The AWS profile to use for the source account (default: default).
    --target-profile TARGET_PROFILE             The AWS profile to use for the target account (default: default).
    --source-region SOURCE_REGION               The AWS region of the source RDS snapshot (default: us-east-1).
    --target-region TARGET_REGION               The AWS region of the target RDS snapshot (optional).

Requirements:
    - boto3
    - typer
    - logging
"""

__author__ = "Bradley Kovaluk"
__version__ = "1.1"
__date__ = "2024-08-07"

import boto3
import logging
import typer
from typing import Optional

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = typer.Typer(help="Copy an RDS snapshot (cluster or instance) between AWS accounts.")


def get_boto3_session(profile_name: str, region_name: str) -> boto3.Session:
    """
    Get a boto3 session for the specified profile and region.
    """
    return boto3.Session(profile_name=profile_name, region_name=region_name)


def copy_snapshot(
    rds_client,
    source_snapshot_name: str,
    target_snapshot_name: str,
    kms_key: Optional[str] = None,
    snapshot_type: str = 'instance'
) -> str:
    """
    Copy the RDS snapshot.
    """
    try:
        if snapshot_type == 'cluster':
            copy_params = {
                'SourceDBClusterSnapshotIdentifier': source_snapshot_name,
                'TargetDBClusterSnapshotIdentifier': target_snapshot_name,
            }
        else:
            copy_params = {
                'SourceDBSnapshotIdentifier': source_snapshot_name,
                'TargetDBSnapshotIdentifier': target_snapshot_name,
            }

        if kms_key:
            copy_params['KmsKeyId'] = kms_key

        if snapshot_type == 'cluster':
            response = rds_client.copy_db_cluster_snapshot(**copy_params)
            snapshot_arn = response['DBClusterSnapshot']['DBClusterSnapshotArn']
            waiter = rds_client.get_waiter('db_cluster_snapshot_available')
            waiter.wait(DBClusterSnapshotIdentifier=target_snapshot_name)
        else:
            response = rds_client.copy_db_snapshot(**copy_params)
            snapshot_arn = response['DBSnapshot']['DBSnapshotArn']
            waiter = rds_client.get_waiter('db_snapshot_available')
            waiter.wait(DBSnapshotIdentifier=target_snapshot_name)

        logger.info(f"Copied snapshot: {snapshot_arn}")
        return snapshot_arn
    except Exception as e:
        logger.error(f"Error copying snapshot: {str(e)}")
        raise


def share_snapshot(
    rds_client,
    snapshot_identifier: str,
    target_account_id: str,
    snapshot_type: str = 'instance'
):
    """
    Share the snapshot with the target account.
    """
    try:
        if snapshot_type == 'cluster':
            rds_client.modify_db_cluster_snapshot_attribute(
                DBClusterSnapshotIdentifier=snapshot_identifier,
                AttributeName='restore',
                ValuesToAdd=[target_account_id]
            )
        else:
            rds_client.modify_db_snapshot_attribute(
                DBSnapshotIdentifier=snapshot_identifier,
                AttributeName='restore',
                ValuesToAdd=[target_account_id]
            )
        logger.info(f"Shared snapshot {snapshot_identifier} with target account: {target_account_id}")
    except Exception as e:
        logger.error(f"Error sharing snapshot with target account: {str(e)}")
        raise


def check_snapshot_type(rds_client, snapshot_name: str) -> str:
    """
    Check if the snapshot is a cluster snapshot or an instance snapshot.
    """
    try:
        rds_client.describe_db_cluster_snapshots(DBClusterSnapshotIdentifier=snapshot_name)
        return 'cluster'
    except rds_client.exceptions.DBClusterSnapshotNotFoundFault:
        return 'instance'


@app.command()
def main(
    source_snapshot_name: str = typer.Argument(..., help="The name of the source RDS snapshot."),
    target_snapshot_name: Optional[str] = typer.Option(
        None,
        "--target-snapshot-name",
        help="The name of the target RDS snapshot (optional).",
    ),
    shared_kms_key: str = typer.Option(
        ..., "--shared-kms-key", help="The shared KMS key ARN."
    ),
    source_account_id: str = typer.Option(
        ..., "--source-account-id", help="The AWS account ID of the source account."
    ),
    target_account_id: str = typer.Option(
        ..., "--target-account-id", help="The AWS account ID of the target account."
    ),
    target_kms_key: Optional[str] = typer.Option(
        None, "--target-kms-key", help="The target KMS key ARN (optional)."
    ),
    source_profile: str = typer.Option(
        "default", "--source-profile", help="The AWS profile to use for the source account."
    ),
    target_profile: str = typer.Option(
        "default", "--target-profile", help="The AWS profile to use for the target account."
    ),
    source_region: str = typer.Option(
        "us-east-1",
        "--source-region",
        help="The AWS region of the source RDS snapshot.",
    ),
    target_region: Optional[str] = typer.Option(
        None,
        "--target-region",
        help="The AWS region of the target RDS snapshot (optional).",
    ),
):
    """
    Copy an RDS snapshot (cluster or instance) between AWS accounts.
    """
    try:
        if not target_snapshot_name:
            target_snapshot_name = source_snapshot_name

        source_session = get_boto3_session(source_profile, source_region)
        target_session = get_boto3_session(target_profile, target_region or source_region)

        source_rds_client = source_session.client('rds')
        target_rds_client = target_session.client('rds')

        # Determine the type of the snapshot (cluster or instance)
        snapshot_type = check_snapshot_type(source_rds_client, source_snapshot_name)

        # Step 1: Copy the source snapshot to the source account using the shared KMS key
        shared_snapshot_name = f"{target_snapshot_name}-share"
        shared_snapshot_arn = copy_snapshot(
            source_rds_client,
            source_snapshot_name,
            shared_snapshot_name,
            shared_kms_key,
            snapshot_type
        )

        # Step 2: Share the snapshot with the target account
        share_snapshot(
            source_rds_client,
            shared_snapshot_name,
            target_account_id,
            snapshot_type
        )

        # Step 3: Copy the snapshot to the target account using the target KMS key (if provided)
        snapshot_identifier = (
            f"arn:aws:rds:{source_region}:{source_account_id}:"
            f"{'cluster-snapshot' if snapshot_type == 'cluster' else 'snapshot'}:{shared_snapshot_name}"
        )
        target_snapshot_arn = copy_snapshot(
            target_rds_client,
            snapshot_identifier,
            target_snapshot_name,
            target_kms_key,
            snapshot_type
        )
        logger.info(f"Snapshot copied to target account: {target_snapshot_arn}")
    except Exception as e:
        logger.error(f"Failed to copy snapshot: {str(e)}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
