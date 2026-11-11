import logging

from marshmallow import ValidationError
from resources import calculate_measures as core_calculate
from util.exceptions import MeasureSoftGramCoreException
from src.config.settings import SUPPORTED_MEASURES

from src.cli.aggregate_metrics import measures as source_measures
from src.cli.aggregate_metrics import metrics as source_metrics
from src.cli.resources.metrics import (
    FILE_METRICS,
    UTS_METRICS,
    get_file_metric_values,
    get_metric_value,
    has_qualifiers,
)
from src.cli.utils import print_warn

logger = logging.getLogger("msgram")


def get_configured_measures(config):
    return [
        measure["key"]
        for characteristic in config["characteristics"]
        for subcharacteristic in characteristic["subcharacteristics"]
        for measure in subcharacteristic["measures"]
    ]


def get_missing_measures(extracted, config, calculated_measures):
    configured_measures = get_configured_measures(config)
    supported_metrics = {
        measure_key: measure_info["metrics"]
        for measure in SUPPORTED_MEASURES
        for measure_key, measure_info in measure.items()
    }

    missing_measures = {}
    for metrics, measures in [
        (source_metrics["sonar"], source_measures["sonarqube"]),
        (source_metrics["github"], source_measures["github"]),
    ]:
        if not any(metric in extracted for metric in metrics):
            continue

        for measure_key in measures:
            if (
                measure_key in configured_measures
                and measure_key not in calculated_measures
            ):
                missing_measures[measure_key] = [
                    metric
                    for metric in supported_metrics[measure_key]
                    if not extracted.get(metric)
                ]

    return missing_measures


def get_measure_value(measures, subchar):
    measures_calculated = []
    for measure in subchar:
        measure_key = measure["key"]
        found = any(measure_key == m["key"] for m in measures)
        if found:
            measures_calculated.append(
                {
                    "key": measure_key,
                    "value": {m["key"]: m["value"] for m in measures}[measure_key],
                    "weight": measure["weight"],
                }
            )

    return measures_calculated


def _supported_measures_for_config(config: dict) -> list[dict]:
    configured_measures = [m for m in get_configured_measures(config) if m]
    if not configured_measures:
        return SUPPORTED_MEASURES
    return [
        measures
        for measures in SUPPORTED_MEASURES
        if list(measures.keys())[0] in configured_measures
    ]


def is_legacy_sonar_extraction(json_data):
    """Arquivo do SonarQube extraído antes de o msgram extract registrar o qualifier."""
    if has_qualifiers(json_data):
        return False
    return any(
        isinstance(measure, dict)
        and measure.get("metric") in FILE_METRICS + UTS_METRICS
        for measures in json_data.values()
        if isinstance(measures, list)
        for measure in measures
    )


def _metric_values_for_measure(json_data, extracted, metric_keys):
    file_metric_keys = [metric for metric in metric_keys if metric in FILE_METRICS]
    if len(file_metric_keys) < 2 or not has_qualifiers(json_data):
        return extracted
    return {**extracted, **get_file_metric_values(json_data, file_metric_keys)}


def calculate_measures(
    json_data,
    config: dict = {
        "characteristics": [{"subcharacteristics": [{"measures": [{"key": ""}]}]}]
    },
):
    extracted = get_metric_value(json_data)

    calculate_infos = []
    for measures in _supported_measures_for_config(config):
        metric_keys = list(measures.values())[0]["metrics"]
        metric_values = _metric_values_for_measure(json_data, extracted, metric_keys)
        calculate_infos.append(
            {
                "key": list(measures.keys())[0],
                "metrics": [
                    {
                        "key": metric,
                        "value": (
                            [float(value) for value in metric_values[metric]]
                            if metric_values.get(metric)
                            else None
                        ),
                    }
                    for metric in metric_keys
                ],
            }
        )
        new_metrics = []
        for measure in calculate_infos:
            if measure.get("metrics", None) and all(
                metric["value"] for metric in measure["metrics"]
            ):
                new_metrics.append(measure)

        calculate_infos = new_metrics

    calculated_measures = [measure["key"] for measure in calculate_infos]
    missing_measures = get_missing_measures(extracted, config, calculated_measures)
    for measure_key, missing_metrics in missing_measures.items():
        print_warn(
            f"Measure '{measure_key}' could not be calculated. "
            f"Missing metrics: {', '.join(missing_metrics)}"
        )

    headers = ["Id", "Name", "Description", "Value", "Created at"]
    return _calculate_each_measure(calculate_infos, config), headers


def _calculate_each_measure(calculate_infos, config):
    """Calcula as medidas uma a uma: um erro do Core numa medida não derruba as outras."""
    result = {"measures": []}
    for measure in calculate_infos:
        try:
            calculated = core_calculate({"measures": [measure]}, config)
        except (MeasureSoftGramCoreException, ValidationError) as error:
            print_warn(f"Measure '{measure['key']}' could not be calculated: {error}")
            continue
        result["measures"].extend(calculated["measures"])
    return result
