#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script: copy_rds_snapshot.py
Description: This script copies an RDS snapshot (cluster or instance) between AWS accounts. It copies the source snapshot
             to the source account using a shared KMS key, shares it with the target account, and then copies it to the
             target account using the target KMS key (if provided).

Usage:
    python copy_rds_snapshot.py <source_snapshot_name> [--target_snapshot_name TARGET_SNAPSHOT_NAME]
                                --shared_kms_key SHARED_KMS_KEY --source_account_id SOURCE_ACCOUNT_ID
                                --target_account_id TARGET_ACCOUNT_ID [--target_kms_key TARGET_KMS_KEY]
                                [--source_profile SOURCE_PROFILE] [--target_profile TARGET_PROFILE]
                                [--source_region SOURCE_REGION] [--target_region TARGET_REGION]

Arguments:
    source_snapshot_name   The name of the source RDS snapshot.

Options:
    --target_snapshot_name TARGET_SNAPSHOT_NAME The name of the target RDS snapshot (optional).
    --shared_kms_key SHARED_KMS_KEY             The shared KMS key ARN.
    --target_kms_key TARGET_KMS_KEY             The target KMS key ARN (optional).
    --source_account_id SOURCE_ACCOUNT_ID       The AWS account ID of the source account.
    --target_account_id TARGET_ACCOUNT_ID       The AWS account ID of the target account.
    --source_profile SOURCE_PROFILE             The AWS profile to use for the source account (default: default).
    --target_profile TARGET_PROFILE             The AWS profile to use for the target account (default: default).
    --source_region SOURCE_REGION               The AWS region of the source RDS snapshot (default: us-east-1).
    --target_region TARGET_REGION               The AWS region of the target RDS snapshot (optional).

Requirements:
    - boto3
    - argparse
    - logging
"""

__author__ = "Bradley Kovaluk"
__version__ = "1.0"
__date__ = "2024-08-07"

import boto3
import argparse
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_boto3_session(profile_name, region_name):
    """
    Get a boto3 session for the specified profile and region.

    Args:
        profile_name (str): The AWS profile to use.
        region_name (str): The AWS region to use.

    Returns:
        boto3.Session: The boto3 session.
    """
    return boto3.Session(profile_name=profile_name, region_name=region_name)

def copy_snapshot(rds_client, source_snapshot_name, target_snapshot_name, kms_key=None, snapshot_type='instance'):
    """
    Copy the RDS snapshot.

    Args:
        rds_client (boto3.client): The RDS client.
        source_snapshot_name (str): The name of the source RDS snapshot.
        target_snapshot_name (str): The name of the target RDS snapshot.
        kms_key (str): The KMS key ARN to use for the snapshot (optional).
        snapshot_type (str): The type of the snapshot ('instance' or 'cluster').

    Returns:
        str: The ARN of the copied snapshot.
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

def share_snapshot(rds_client, snapshot_arn, target_account_id, snapshot_type='instance'):
    """
    Share the snapshot with the target account.

    Args:
        rds_client (boto3.client): The RDS client.
        snapshot_arn (str): The ARN of the snapshot to share.
        target_account_id (str): The AWS account ID of the target account.
        snapshot_type (str): The type of the snapshot ('instance' or 'cluster').

    Raises:
        Exception: If sharing the snapshot fails.
    """
    try:
        if snapshot_type == 'cluster':
            rds_client.modify_db_cluster_snapshot_attribute(
                DBClusterSnapshotIdentifier=snapshot_arn,
                AttributeName='restore',
                ValuesToAdd=[target_account_id]
            )
        else:
            rds_client.modify_db_snapshot_attribute(
                DBSnapshotIdentifier=snapshot_arn,
                AttributeName='restore',
                ValuesToAdd=[target_account_id]
            )
        logger.info(f"Shared snapshot {snapshot_arn} with target account: {target_account_id}")
    except Exception as e:
        logger.error(f"Error sharing snapshot with target account: {str(e)}")
        raise

def check_snapshot_type(rds_client, snapshot_name):
    """
    Check if the snapshot is a cluster snapshot or an instance snapshot.

    Args:
        rds_client (boto3.client): The RDS client.
        snapshot_name (str): The name of the RDS snapshot.

    Returns:
        str: The type of the snapshot ('instance' or 'cluster').
    """
    try:
        rds_client.describe_db_cluster_snapshots(DBClusterSnapshotIdentifier=snapshot_name)
        return 'cluster'
    except rds_client.exceptions.DBClusterSnapshotNotFoundFault:
        return 'instance'

def main(source_snapshot_name, target_snapshot_name, shared_kms_key, source_account_id, target_account_id, source_profile, target_profile, source_region, target_region, target_kms_key=None):
    """
    Main function to copy an RDS snapshot between AWS accounts.

    Args:
        source_snapshot_name (str): The name of the source RDS snapshot.
        target_snapshot_name (str): The name of the target RDS snapshot.
        shared_kms_key (str): The shared KMS key ARN.
        target_kms_key (str): The target KMS key ARN (optional).
        source_account_id (str): The AWS account ID of the source account.
        target_account_id (str): The AWS account ID of the target account.
        source_profile (str): The AWS profile to use for the source account.
        target_profile (str): The AWS profile to use for the target account.
        source_region (str): The AWS region of the source RDS snapshot.
        target_region (str): The AWS region of the target RDS snapshot.
    """
    source_session = get_boto3_session(source_profile, source_region)
    target_session = get_boto3_session(target_profile, target_region or source_region)

    source_rds_client = source_session.client('rds')
    target_rds_client = target_session.client('rds')

    # Determine the type of the snapshot (cluster or instance)
    snapshot_type = check_snapshot_type(source_rds_client, source_snapshot_name)

    # Step 1: Copy the source snapshot to the source account using the shared KMS key
    shared_snapshot_arn = copy_snapshot(source_rds_client, source_snapshot_name, target_snapshot_name + '-share', shared_kms_key, snapshot_type)

    # Step 2: Share the snapshot with the target account
    share_snapshot(source_rds_client, shared_snapshot_arn, target_account_id, snapshot_type)

    # Step 3: Copy the snapshot to the target account using the target KMS key (if provided)
    copy_snapshot(target_rds_client, shared_snapshot_arn, target_snapshot_name, target_kms_key, snapshot_type)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Copy an RDS snapshot between AWS accounts")
    parser.add_argument("source_snapshot_name", help="The name of the source RDS snapshot")
    parser.add_argument("--target_snapshot_name", help="The name of the target RDS snapshot (optional)")
    parser.add_argument("--shared_kms_key", required=True, help="The shared KMS key ARN")
    parser.add_argument("--target_kms_key", help="The target KMS key ARN (optional)")
    parser.add_argument("--source_account_id", required=True, help="The AWS account ID of the source account")
    parser.add_argument("--target_account_id", required=True, help="The AWS account ID of the target account")
    parser.add_argument("--source_profile", default="default", help="The AWS profile to use for the source account (default: default)")
    parser.add_argument("--target_profile", default="default", help="The AWS profile to use for the target account (default: default)")
    parser.add_argument("--source_region", default="us-east-1", help="The AWS region of the source RDS snapshot (default: us-east-1)")
    parser.add_argument("--target_region", help="The AWS region of the target RDS snapshot (optional)")

    args = parser.parse_args()

    target_snapshot_name = args.target_snapshot_name if args.target_snapshot_name else args.source_snapshot_name

    main(
        source_snapshot_name=args.source_snapshot_name,
        target_snapshot_name=target_snapshot_name,
        shared_kms_key=args.shared_kms_key,
        target_kms_key=args.target_kms_key,
        source_account_id=args.source_account_id,
        target_account_id=args.target_account_id,
        source_profile=args.source_profile,
        target_profile=args.target_profile,
        source_region=args.source_region,
        target_region=args.target_region or args.source_region
    )
