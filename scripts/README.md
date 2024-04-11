# Virtual Environment and Script Runner

This Python script sets up a virtual environment, installs requirements, and runs a specified Python script within the virtual environment.

## Usage

1. Ensure that Python 3 is installed on your system.

2. Clone or download the project repository to your local machine.

3. Navigate to the project directory.

4. Open a terminal or command prompt.

5. Run the script using the following command:

    `python runscript.py <base_dir> <script_file>`  

    >Replace `<base_dir>` with the base directory path containing the `requirements.txt` file and the Python script file you want to run. Replace `<script_file>` with the filename of the Python script you want to execute.

6. The script will create a virtual environment, upgrade `pip`, install the requirements from the `requirements.txt` file, and run the specified Python script within the virtual environment.

7. The script will log the progress and important steps to the console.

8. Once the script completes, the Python script specified will be executed within the virtual environment.

## Requirements

- Python 3

## Logging

The script utilizes the `logging` module to provide informative log messages during the execution. The log messages will be displayed in the console. The logging level is set to `INFO`.

