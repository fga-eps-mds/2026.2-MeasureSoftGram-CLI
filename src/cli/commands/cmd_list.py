from src.cli.i18n import _
from src.cli.utils import (
    clear_console,
    color_tag,
    console,
    print_error,
    print_info,
    print_rule,
)

from src.config.settings import (
    FILE_CONFIG,
    DEFAULT_CONFIG_PATH,
    DEFAULT_CONFIG_FILE_PATH,
)

from pathlib import Path

import json
import os
import sys


def print_json_tree(data):
    result = []
    stack = [(data, "")]
    is_top = True
    main_color = color_tag("main")
    success_color = color_tag("success")

    measure_to_metric = {}
    measure_to_metric["passed_tests"] = ["tests", "test_failures", "test_errors"]
    measure_to_metric["test_builds"] = ["tests", "test_execution_time"]
    measure_to_metric["test_coverage"] = ["coverage"]
    measure_to_metric["non_complex_file_density"] = ["functions", "complexity"]
    measure_to_metric["commented_file_density"] = ["comment_lines_density"]
    measure_to_metric["duplication_absense"] = ["duplicated_lines_density"]
    measure_to_metric["technical_debt_ratio"] = ["sqale_debt_ratio"]
    measure_to_metric["team_throughput"] = ["resolved_issues", "total_issues"]
    measure_to_metric["ci_feedback_time"] = ["sum_ci_feedback_times", "total_builds"]

    while stack:
        data, indent = stack.pop()
        key = data.get("key")

        if is_top:
            result.append(f"{main_color}\n" + _("Characteristic:"))
            is_top = False
        result.append(f"{main_color}{indent}{success_color}{key}")

        weight = data.get("weight", 0)
        result.append(f"{main_color}{indent}{_('Weight:')} {success_color}{weight}%")

        if "subcharacteristics" in data:
            for subchar in data["subcharacteristics"]:
                result.append(f"{main_color}{indent}" + _("Sub-characteristic(s):"))
                stack.append(
                    (subchar, f"{indent}│  ")
                )  # Use the ASCII character │ (code 179)

        if "measures" in data:
            for measure in data["measures"]:
                result.append(f"{main_color}{indent}│  " + _("Measure(s):"))
                measure_key = measure.get("key")
                result.append(
                    f"{main_color}{indent}{indent}│  {success_color}{measure_key}"
                )
                result.append(
                    f"{main_color}{indent}{indent}│  {_('Weight:')} "
                    f"{success_color}{measure['weight']}%"
                )
                if "min_threshold" in measure and "max_threshold" in measure:
                    min_threshold = measure.get("min_threshold")
                    max_threshold = measure.get("max_threshold")
                    result.append(f"{main_color}{indent}{indent}│  " + _("Metric(s):"))
                    metrics = measure_to_metric.get(
                        measure_key, []
                    )  # Get associated metrics
                    min_max = ""
                    for metric in metrics:
                        result.append(
                            f"{main_color}{indent}{indent}│  └─{success_color}{metric}"
                        )
                        min_max = _("Min = {min} and Max = {max}").format(
                            min=f"{success_color}{min_threshold}{main_color}",
                            max=f"{success_color}{max_threshold}",
                        )
                    result.append(
                        f"{main_color}{indent}{indent}│  │ "
                        + _("Reference values: {range}").format(range=min_max)
                    )
                    result.append(
                        f"{main_color}{indent}{indent}│  " + _("End-Metric(s)")
                    )
                result.append(f"{main_color}{indent}│  " + _("End-Measure(s)"))
            result.append(f"{main_color}" + _("End-SubCharacteristic"))
    result.append(f"{main_color}" + _("End-Characteristic"))

    return "\n".join(result)


def command_list(args):
    clear_console()

    file_path = DEFAULT_CONFIG_FILE_PATH
    try:
        config_path: Path = args["config_path"]

        if config_path != DEFAULT_CONFIG_PATH:
            print_info(_("The user-provided file will be used: "))
            file_path = str(config_path) + "/msgram.json"
        else:
            print_info(
                _(
                    "No configuration file path was given, the default path will be used."
                )
            )

    except Exception as e:
        print_error(
            _("KeyError: args[{error}] - non-existent parameters").format(error=e)
        )
        exit(1)

    print_rule(_("Listing Configuration Parameters"))

    if not (os.path.exists(file_path)):
        print_info(_("The configuration file was not found. \n"))
        print_info(_("Run 'msgram init' in the desired project to create it.\n"))
        print_info(
            _("Or use 'msgram init --config_path <path>' to give the path to the file.")
        )
        sys.exit(1)

    print_info(
        _("MSGram config file '{file}' exists already!").format(file=FILE_CONFIG)
    )

    f = open(file_path)

    data = json.load(f)

    for characteristic in data.get("characteristics", []):
        output_string = print_json_tree(characteristic)
        print_info(output_string)

    console.line()
    print_info(_("To set the weights by pairwise comparison, use: msgram weights"))
    print_info(_("To set the weights manually, use: `vim .msgram/msgram.json`"))
