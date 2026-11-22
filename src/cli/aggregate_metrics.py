import os
import json

from src.cli.i18n import _
from src.cli.utils import print_error, print_info, print_success

metrics = {}
metrics["sonar"] = [
    "tests",
    "test_failures",
    "test_errors",
    "coverage",
    "test_execution_time",
    "functions",
    "complexity",
    "comment_lines_density",
    "duplicated_lines_density",
    "sqale_debt_ratio",
]

metrics["github"] = [
    "resolved_issues",
    "total_issues",
    "sum_ci_feedback_times",
    "total_builds",
]

measures = {}
measures["sonarqube"] = [
    "passed_tests",
    "test_builds",
    "test_errors",
    "test_coverage",
    "non_complex_file_density",
    "commented_file_density",
    "duplication_absense",
    "technical_debt_ratio",
]

measures["github"] = ["team_throughput", "ci_feedback_time"]


def should_process_metrics(config):
    for characteristic in config.get("characteristics", []):
        for subcharacteristic in characteristic.get("subcharacteristics", []):
            for measure in subcharacteristic.get("measures", []):
                if (
                    measure.get("key") not in measures["sonarqube"]
                    and measure.get("key") not in measures["github"]
                ):
                    return False
    return True


def read_msgram(file_path):
    try:
        with open(file_path, "r") as file:
            return json.load(file)
    except IsADirectoryError as e:
        print_error(_("> Error: {error}").format(error=e))
        return False
    except FileNotFoundError as e:
        print_error(_("> Error: {error}").format(error=e))
        return False


def list_msgram_files(folder_path):
    try:
        if not os.path.isdir(folder_path):
            raise NotADirectoryError(f"{folder_path} is not a directory.")

        msgram_files = [
            file for file in os.listdir(folder_path) if file.endswith(".msgram")
        ]
        return msgram_files

    except NotADirectoryError as e:
        print_error(_("> Error: {error}").format(error=e))
        return False


def save_metrics(file_name, metrics):
    directory = os.path.dirname(file_name)

    os.makedirs(directory, exist_ok=True)

    output_file_path = os.path.join(
        directory, os.path.basename(file_name).replace(".msgram", ".metrics")
    )
    with open(output_file_path, "w") as output_file:
        json.dump(metrics, output_file, indent=2)

    print_success(_("> Metrics saved to: {path}\n").format(path=output_file_path))


def process_metrics(folder_path, msgram_files):
    processed_files = []

    for file in msgram_files:
        print_info(_("> Processing {file}").format(file=file))
        metrics_dict = read_msgram(os.path.join(folder_path, file))

        if not metrics_dict:
            print_error(
                _("> Error to read metrics in: {path}\n").format(path=folder_path)
            )
            return False

        processed_files.append((file, metrics_dict))

    return processed_files


def aggregate_metrics(input_format, folder_path, config: json):
    msgram_files = list_msgram_files(folder_path)

    if not msgram_files:
        print_error(_("> Error: Can not read msgram files in provided directory"))
        return False

    github_files = [file for file in msgram_files if file.startswith("github_")]
    sonar_files = [file for file in msgram_files if file not in github_files]
    file_content = {}

    result = []

    have_metrics = False

    if should_process_metrics(config):
        result = process_metrics(
            folder_path, github_files if input_format == "github" else sonar_files
        )

        if not result:
            print_error(_("> Error: Unexpected result from process_github_metrics"))
            return False

        have_metrics = True
    else:
        print_error(_("> Error: Unexpected measures from should_process_metrics"))
        return False

    if not have_metrics:
        print_error(
            _(
                "> Error: No metrics where found in the .msgram files from the type: {input_format}"
            ).format(input_format=input_format)
        )
        return False

    for filename, file_content in result:
        save_metrics(os.path.join(folder_path, filename), file_content)

    return True
