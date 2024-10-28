# Run Script in Virtual Environment

This script sets up a Python virtual environment in a specified directory, installs dependencies from a `requirements.txt` file, and runs a specified Python script within the environment. This setup ensures that the script runs with isolated dependencies, avoiding conflicts with other projects.

## Features

- Automatically creates a virtual environment if it doesn’t already exist.
- Upgrades `pip` in the virtual environment.
- Installs dependencies from `requirements.txt`.
- Executes a specified Python script within the virtual environment.
- Provides detailed logging of each step.

## Requirements

- Python 3.11+ (includes `venv` for virtual environment creation)
- `Typer` and `Rich` libraries for enhanced CLI and logging

## Usage

### Command

~~~
python run_script.py <base_dir> <script_file>
~~~

### Arguments

- `base_dir`: The base directory path where the virtual environment will be created.
- `script_file`: The Python script to be executed within the virtual environment.

### Example

To run `my_script.py` within a virtual environment located at `/path/to/project`:

~~~
python run_script.py /path/to/project my_script.py
~~~

## Script Overview

1. **Create Virtual Environment**: Sets up a `venv` in the specified `base_dir` if it doesn't already exist.
2. **Upgrade Pip**: Upgrades `pip` within the virtual environment.
3. **Install Dependencies**: Installs dependencies from the `requirements.txt` file in `base_dir`.
4. **Run Script**: Executes the specified `script_file` using the environment’s Python interpreter.

## Logging

The script provides detailed logging for each action, including success messages and error notifications, to make troubleshooting easier.

## Error Handling

If any step fails (e.g., virtual environment creation, pip upgrade, dependency installation, or script execution), the script will log the error and exit gracefully.

## License

This project is licensed under the MIT License.
