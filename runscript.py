import os
import sys
import platform
from subprocess import check_call
import logging


def create_venv(base_dir):
    """
    Create a virtual environment if it doesn't already exist.

    Args:
        base_dir (str): The base directory path.

    """
    venv_path = os.path.join(base_dir, 'venv')
    if not os.path.exists(venv_path):
        check_call([sys.executable, '-m', 'venv', venv_path])
        logging.info("Virtual environment created.")


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
    check_call([venv_python, '-m', 'pip', 'install', '--upgrade', 'pip'])
    logging.info("pip upgraded.")


def install_requirements(base_dir):
    """
    Install requirements from the requirements.txt file within the virtual environment.

    Args:
        base_dir (str): The base directory path.

    """
    venv_python = get_python_executable(base_dir)
    requirements_path = os.path.join(base_dir, 'requirements.txt')
    check_call([venv_python, '-m', 'pip', 'install', '-r', requirements_path])
    logging.info("Requirements installed.")


def run_python_script(base_dir, script_file):
    """
    Run the specified Python script within the virtual environment.

    Args:
        base_dir (str): The base directory path.
        script_file (str): The path to the Python script file.

    """
    venv_python = get_python_executable(base_dir)
    check_call([venv_python, script_file])  # Removed os.path.join here, might add it back later
    logging.info("Python script executed.")


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python runscript.py <base_dir> <script_file_path>")
        sys.exit(1)

    base_dir = sys.argv[1]
    script_file = sys.argv[2]

    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logging.info("Starting script.")

    # Create virtual environment
    create_venv(base_dir)

    # Upgrade pip
    upgrade_pip(base_dir)

    # Install requirements
    install_requirements(base_dir)

    # Run Python script
    run_python_script(base_dir, script_file)

    logging.info("Script execution completed.")
