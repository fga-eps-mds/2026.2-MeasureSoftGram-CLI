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

    lines = [f"{main_color}{indent}{indent}│  Métrica(s):"]
    min_max = ""
    for metric in metrics:
        lines.append(f"{main_color}{indent}{indent}│  └─{success_color}{metric}")
        min_max = (
            f"Min = {success_color}{min_threshold} {main_color}"
            f"e Max = {success_color}{max_threshold}"
        )
    lines.append(f"{main_color}{indent}{indent}│  │ Valores de referência: {min_max}")
    lines.append(f"{main_color}{indent}{indent}│  Fim-Métrica(s)")
    return lines


def _format_single_measure(measure, indent, main_color, success_color):
    measure_key = measure.get("key")
    lines = [
        f"{main_color}{indent}│  Medida(s):",
        f"{main_color}{indent}{indent}│  {success_color}{measure_key}",
        f"{main_color}{indent}{indent}│  Peso: {success_color}{measure['weight']}%",
    ]
    lines.extend(_format_measure_metrics(measure, indent, main_color, success_color))
    lines.append(f"{main_color}{indent}│  Fim-Medida(s)")
    return lines


def _format_measures(measures, indent, main_color, success_color):
    lines = []
    for measure in measures:
        lines.extend(_format_single_measure(measure, indent, main_color, success_color))
    lines.append(f"{main_color}Fim-SubCaracterística")
    return lines


def _process_subcharacteristics(subcharacteristics, indent, main_color, stack):
    lines = []
    for subchar in subcharacteristics:
        lines.append(f"{main_color}{indent}Sub-característica(s):")
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
            result.append(f"{main_color}\nCaracterística:")
            is_top = False
        result.append(f"{main_color}{indent}{success_color}{key}")

        weight = data.get("weight", 0)
        result.append(f"{main_color}{indent}Peso: {success_color}{weight}%")

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

    result.append(f"{main_color}Fim-Característica")

    return "\n".join(result)


def command_list(args):
    clear_console()

    file_path = DEFAULT_CONFIG_FILE_PATH
    try:
        config_path: Path = args["config_path"]

        if config_path != DEFAULT_CONFIG_PATH:
            print_info("Será usado arquivo informado pelo usuário: ")
            file_path = str(config_path) + "/msgram.json"
        else:
            print_info(
                "Não foi informado caminho do arquivo de configuração, será usado caminho padrão."
            )

    except Exception as e:
        print_error(f"KeyError: args[{e}] - non-existent parameters")
        exit(1)

    print_rule("Listing Configuration Parameters")

    if not (os.path.exists(file_path)):
        print_info("O arquivo de configuração não foi encontrado. \n")
        print_info(
            "Execute o comando 'msgram init' no projeto desejado para criá-lo.\n"
        )
        print_info(
            "Ou use 'msgram init --config_path <path>' para informar o caminho ate o arquivo."
        )
        sys.exit(1)

    print_info(f"MSGram config file '{FILE_CONFIG}' exists already!")

    f = open(file_path)

    data = json.load(f)

    for characteristic in data.get("characteristics", []):
        output_string = print_json_tree(characteristic)
        print_info(output_string)

    console.line()
    print_info("Para definir os pesos por comparação, use: msgram weights")
    print_info("Para definir os pesos de forma manual, use: `vim .msgram/msgram.json`")

    weight_errors = validate_weights(data)
    if weight_errors:
        # DOC#302: mostra a configuração e, no fim, o mesmo erro do calculate
        console.line()
        print_weight_errors(weight_errors, file_path)
        sys.exit(1)
