# Package Lambda Function

This script packages a Python Lambda function, including dependencies from a `requirements.txt` file, into a zip file for AWS deployment. It provides options to use Docker for Lambda-compatible packaging, specify the Python version, and choose a custom requirements file. Common Lambda runtime packages like `boto3` and `botocore` are automatically excluded.

## Features

- **Flexible Dependency Packaging**: Use Docker or local installation for Lambda compatibility.
- **Customizable Python Version**: Specify a Python version compatible with Lambda.
- **Automatic Exclusions**: Excludes `boto3` and `botocore` (available in Lambda runtime).
- **Detailed Logging**: Rich, configurable logging with error handling.

## Requirements

- Python 3.8+
- `Typer` and `Rich` libraries
- Docker (optional, for Lambda-compatible packaging)

## Usage

### Command

~~~sh
python package_lambda.py <base_dir> [--log-level LOG_LEVEL] [--use-docker] [--python-version PYTHON_VERSION] [--requirements-file REQUIREMENTS_FILE]
~~~

### Arguments

- `base_dir` (required): Base directory path of the Lambda function.

### Options

- `--log-level LOG_LEVEL`: Set logging level (default: INFO).
- `--use-docker`: Use Docker for Lambda-compatible dependency packaging.
- `--python-version PYTHON_VERSION`: Specify Python version (default: 3.8).
- `--requirements-file REQUIREMENTS_FILE`: Path to requirements file (default: `requirements.txt`).

### Example

To package a Lambda function with Docker and a custom Python version:

~~~sh
python package_lambda.py /path/to/lambda --use-docker --python-version 3.9 --log-level DEBUG
~~~

## Script Highlights

1. **Dependency Installation**: Installs dependencies in `package/` (Docker or local).
2. **Exclusion Handling**: Skips `boto3` and `botocore` by default.
3. **Packaging**: Packages Lambda code and dependencies into a zip file in `release/`.

This script provides a flexible, efficient solution for preparing Lambda deployment packages, with clear logging and customizable options for streamlined packaging.
