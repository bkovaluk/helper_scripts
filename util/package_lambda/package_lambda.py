#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script: package_lambda.py
Description: This script packages a Python Lambda function, including dependencies from a requirements.txt file, into a zip file for deployment.
             It excludes packages that are already included in the AWS Lambda runtime.

Usage:
    python package_lambda.py <base_dir> [--log-level LOG_LEVEL]

Arguments:
    base_dir          The base directory path of the Lambda function.

Options:
    --log-level LOG_LEVEL The logging level (default: INFO).

Requirements:
    - venv
    - pip
    - logging
"""

__author__ = "Bradley Kovaluk"
__version__ = "1.2"
__date__ = "2023-10-29"

import os
import platform
import shutil
import zipfile
import logging
import argparse
import venv
import subprocess

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

EXCLUDED_PACKAGES = ['boto3', 'botocore']

def create_venv(base_dir):
    """
    Create a virtual environment if it doesn't already exist.

    Args:
        base_dir (str): The base directory path.

    """
    venv_path = os.path.join(base_dir, 'venv')
    if not os.path.exists(venv_path):
        logger.info("Creating virtual environment...")
        venv.create(venv_path, with_pip=True)
        logger.info("Virtual environment created.")
    else:
        logger.info("Virtual environment already exists.")

def get_python_executable(base_dir):
    """
    Get the path to the Python executable within the virtual environment.

    Args:
        base_dir (str): The base directory path.

    Returns:
        str: The path to the Python executable.

    """
    venv_python = os.path.join(base_dir, 'venv', 'bin', 'python')
    if platform.system() == 'Windows':
        venv_python = os.path.join(base_dir, 'venv', 'Scripts', 'python.exe')
    return venv_python

def upgrade_pip(base_dir):
    """
    Upgrade pip within the virtual environment.

    Args:
        base_dir (str): The base directory path.

    """
    venv_python = get_python_executable(base_dir)
    logger.info("Upgrading pip...")
    subprocess.check_call([venv_python, '-m', 'pip', 'install', '--upgrade', 'pip'])
    logger.info("pip upgraded.")

def install_requirements(base_dir):
    """
    Install requirements from the requirements.txt file within the virtual environment.

    Args:
        base_dir (str): The base directory path.

    """
    venv_python = get_python_executable(base_dir)
    requirements_path = os.path.join(base_dir, 'requirements.txt')
    if os.path.exists(requirements_path):
        logger.info("Installing requirements...")
        subprocess.check_call([venv_python, '-m', 'pip', 'install', '-r', requirements_path])
        logger.info("Requirements installed.")
    else:
        logger.warning("requirements.txt not found. Skipping dependency installation.")

def uninstall_excluded_packages(base_dir):
    """
    Uninstall packages that are included in the AWS Lambda runtime.

    Args:
        base_dir (str): The base directory path.
    """
    venv_python = get_python_executable(base_dir)
    for package in EXCLUDED_PACKAGES:
        logger.info(f"Uninstalling {package}...")
        subprocess.call([venv_python, '-m', 'pip', 'uninstall', '-y', package])

def package_lambda(base_dir):
    """
    Package the Lambda function and its dependencies.

    Args:
        base_dir (str): The base directory path.

    """
    release_dir = os.path.join(base_dir, 'release')

    # Delete the release directory if it already exists
    if os.path.exists(release_dir):
        shutil.rmtree(release_dir)

    # Create the release directory
    os.makedirs(release_dir, exist_ok=True)

    # Determine the site-packages directory within the virtual environment
    site_packages_dir = os.path.join(base_dir, 'venv', 'lib',
                                     'python%s' % platform.python_version()[:3], 'site-packages')
    if platform.system() == 'Windows':
        site_packages_dir = os.path.join(base_dir, 'venv', 'Lib', 'site-packages')

    # Copy everything from site-packages to the release directory
    copytree(site_packages_dir, release_dir)

    # Copy everything else from the base directory to the release directory,
    # excluding the virtual environment, the release directory itself, and the 'tests' directory
    for item in os.listdir(base_dir):
        item_path = os.path.join(base_dir, item)
        if os.path.isdir(item_path) and item not in ['venv', 'release', 'tests']:
            copytree(item_path, os.path.join(release_dir, item))
        elif os.path.isfile(item_path):
            shutil.copy2(item_path, release_dir)

    zip_release(base_dir)

    logger.info("Lambda function packaged.")

def copytree(src, dst, symlinks=False, ignore=None):
    """
    This function is a slightly modified version of shutil.copytree.
    It can handle the case where the destination directory already exists
    and explicitly creates directories before copying files.

    """
    if not os.path.exists(dst):
        os.makedirs(dst)

    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            copytree(s, d, symlinks, ignore)
        else:
            shutil.copy2(s, d)

def zip_release(base_dir):
    """
    Create a zip file from the contents of the release directory.

    Args:
        base_dir (str): The base directory path.

    """
    release_dir = os.path.join(base_dir, 'release')

    # Use the base directory name as the zip file name
    zip_file_name = os.path.basename(os.path.normpath(base_dir)) + '.zip'
    zipf = zipfile.ZipFile(os.path.join(base_dir, zip_file_name), 'w', zipfile.ZIP_DEFLATED)

    for root, dirs, files in os.walk(release_dir):
        for file in files:
            # Create a relative path to preserve directory structure within the zip
            relative_path = os.path.relpath(os.path.join(root, file), release_dir)
            zipf.write(os.path.join(root, file), arcname=relative_path)

    zipf.close()
    logger.info("Created zip file from release directory.")

def main(base_dir, log_level='INFO'):
    """
    Main function to package the Lambda function and its dependencies.

    Args:
        base_dir (str): The base directory path.
        log_level (str): The logging level to use.
    """
    logging.getLogger().setLevel(log_level.upper())
    logger.info("Starting script.")

    try:
        # Create virtual environment
        create_venv(base_dir)

        # Upgrade pip
        upgrade_pip(base_dir)

        # Install requirements
        install_requirements(base_dir)

        # Uninstall excluded packages
        uninstall_excluded_packages(base_dir)

        # Package Lambda function
        package_lambda(base_dir)

        logger.info("Script execution completed.")
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Package a Python Lambda function, including dependencies from a requirements.txt file, into a zip file for deployment.")
    parser.add_argument('base_dir', help="The base directory path of the Lambda function.")
    parser.add_argument('--log-level', default='INFO', help="The logging level to use (default: INFO).")
    args = parser.parse_args()

    main(args.base_dir, args.log_level)
