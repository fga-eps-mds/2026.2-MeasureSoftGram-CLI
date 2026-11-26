from src.cli.i18n import _
from src.cli.resources.weights import print_weight_errors, validate_weights
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

MEASURE_TO_METRIC = {
    "passed_tests": ["tests", "test_failures", "test_errors"],
    "test_builds": ["tests", "test_execution_time"],
    "test_coverage": ["coverage"],
    "non_complex_file_density": ["functions", "complexity"],
    "commented_file_density": ["comment_lines_density"],
    "duplication_absense": ["duplicated_lines_density"],
    "technical_debt_ratio": ["sqale_debt_ratio"],
    "team_throughput": ["resolved_issues", "total_issues"],
    "ci_feedback_time": ["sum_ci_feedback_times", "total_builds"],
}


def _format_measure_metrics(measure, indent, main_color, success_color):
    if "min_threshold" not in measure or "max_threshold" not in measure:
        return []

    min_threshold = measure.get("min_threshold")
    max_threshold = measure.get("max_threshold")
    measure_key = measure.get("key")
    metrics = MEASURE_TO_METRIC.get(measure_key, [])

    lines = [f"{main_color}{indent}{indent}│  " + _("Metric(s):")]
    min_max = ""
    for metric in metrics:
        lines.append(f"{main_color}{indent}{indent}│  └─{success_color}{metric}")
        min_max = _("Min = {min} and Max = {max}").format(
            min=f"{success_color}{min_threshold}{main_color}",
            max=f"{success_color}{max_threshold}",
        )
    lines.append(
        f"{main_color}{indent}{indent}│  │ "
        + _("Reference values: {range}").format(range=min_max)
    )
    lines.append(f"{main_color}{indent}{indent}│  " + _("End-Metric(s)"))
    return lines


def _format_single_measure(measure, indent, main_color, success_color):
    measure_key = measure.get("key")
    lines = [
        f"{main_color}{indent}│  " + _("Measure(s):"),
        f"{main_color}{indent}{indent}│  {success_color}{measure_key}",
        f"{main_color}{indent}{indent}│  {_('Weight:')} {success_color}{measure['weight']}%",
    ]
    lines.extend(_format_measure_metrics(measure, indent, main_color, success_color))
    lines.append(f"{main_color}{indent}│  " + _("End-Measure(s)"))
    return lines


def _format_measures(measures, indent, main_color, success_color):
    lines = []
    for measure in measures:
        lines.extend(_format_single_measure(measure, indent, main_color, success_color))
    lines.append(f"{main_color}" + _("End-SubCharacteristic"))
    return lines


def _process_subcharacteristics(subcharacteristics, indent, main_color, stack):
    lines = []
    for subchar in subcharacteristics:
        lines.append(f"{main_color}{indent}" + _("Sub-characteristic(s):"))
        stack.append((subchar, f"{indent}│  "))  # Use the ASCII character │ (code 179)
    return lines


def print_json_tree(data):
    result = []
    stack = [(data, "")]
    is_top = True
    main_color = color_tag("main")
    success_color = color_tag("success")

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
            result.extend(
                _process_subcharacteristics(
                    data["subcharacteristics"], indent, main_color, stack
                )
            )

        if "measures" in data:
            result.extend(
                _format_measures(data["measures"], indent, main_color, success_color)
            )

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

    weight_errors = validate_weights(data)
    if weight_errors:
        # DOC#302: mostra a configuração e, no fim, o mesmo erro do calculate
        console.line()
        print_weight_errors(weight_errors, file_path)
        sys.exit(1)
