# Package Lambda Function

This script packages a Python Lambda function, including dependencies from a `requirements.txt` file, into a zip file for deployment. It excludes packages that are already included in the AWS Lambda runtime, such as `boto3` and `botocore`.

## Features

- Creates a virtual environment for the Lambda function.
- Installs dependencies listed in `requirements.txt`.
- Excludes packages that are already available in the AWS Lambda runtime.
- Packages the Lambda function and its dependencies into a zip file for deployment.
- Provides detailed logging and error handling.
- Allows the user to set the logging level.

## Requirements

- Python 3.6 or higher
- `venv` module
- `pip`
- `argparse`
- `logging`
- `shutil`
- `zipfile`
- `subprocess`
- `platform`

## Usage

### Command

```sh
python package_lambda.py <base_dir> [--log-level LOG_LEVEL]
```

### Arguments

- `base_dir` (required): The base directory path of the Lambda function.

### Options

- `--log-level LOG_LEVEL` (optional): The logging level to use (default: INFO).

### Example

To package a Lambda function with a specified base directory and logging level:

```sh
python package_lambda.py /path/to/lambda --log-level DEBUG
```

## Script Details

### Functions

1. **create_venv(base_dir)**:
   - Creates a virtual environment in the specified base directory if it doesn't already exist.

2. **get_python_executable(base_dir)**:
   - Retrieves the path to the Python executable within the virtual environment.

3. **upgrade_pip(base_dir)**:
   - Upgrades `pip` within the virtual environment.

4. **install_requirements(base_dir)**:
   - Installs dependencies from the `requirements.txt` file within the virtual environment.

5. **uninstall_excluded_packages(base_dir)**:
   - Uninstalls packages that are included in the AWS Lambda runtime, such as `boto3` and `botocore`.

6. **package_lambda(base_dir)**:
   - Packages the Lambda function and its dependencies into a zip file for deployment.

7. **copytree(src, dst, symlinks=False, ignore=None)**:
   - Copies the contents of the source directory to the destination directory.

8. **zip_release(base_dir)**:
   - Creates a zip file from the contents of the release directory.

### Logging Levels

- `DEBUG`: Detailed information, typically of interest only when diagnosing problems.
- `INFO`: Confirmation that things are working as expected.
- `WARNING`: An indication that something unexpected happened or indicative of some problem in the near future (e.g., ‘disk space low’). The software is still working as expected.
- `ERROR`: Due to a more serious problem, the software has not been able to perform some function.
- `CRITICAL`: A serious error, indicating that the program itself may be unable to continue running.

### Logging Format

The script logs messages with the following format:

```plaintext
<timestamp> - <log level> - <message>
```

### Error Handling

The script includes error handling to catch exceptions and log error messages, ensuring that any issues are properly reported and can be addressed.