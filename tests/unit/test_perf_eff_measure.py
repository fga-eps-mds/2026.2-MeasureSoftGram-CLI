from pathlib import Path

import pytest

from src.cli.resources.perf_eff_measure import (
    build_json_output,
    calculate_perf_eff_measures,
    get_value_by_key,
    make_characteristics_input,
    make_subcharacteristics_input,
)
from src.cli.resources.perf_eff_parser import parse_performance_efficiency_data


def test_get_value_by_key_found():
    data = [
        {"key": "response_time", "value": 0.85},
        {"key": "cpu_utilization", "value": 0.65},
        {"key": "memory_utilization", "value": 0.45},
    ]

    assert get_value_by_key(data, "response_time") == 0.85
    assert get_value_by_key(data, "memory_utilization") == 0.45


def test_get_value_by_key_not_found():
    data = [
        {"key": "response_time", "value": 0.85},
    ]

    assert get_value_by_key(data, "non_existent_key") is None
    assert get_value_by_key([], "response_time") is None


def test_make_subcharacteristics_input():
    calculated_measures = [
        {"key": "cpu_utilization", "value": 0.75},
        {"key": "memory_utilization", "value": 0.55},
        {"key": "response_time", "value": 0.90},
    ]

    result = make_subcharacteristics_input(calculated_measures)

    assert result == {
        "subcharacteristics": [
            {
                "key": "time_behaviour",
                "measures": [
                    {
                        "key": "response_time",
                        "value": 0.90,
                        "weight": 100,
                    },
                ],
            },
            {
                "key": "resource_utilization",
                "measures": [
                    {
                        "key": "cpu_utilization",
                        "value": 0.75,
                        "weight": 50,
                    },
                    {
                        "key": "memory_utilization",
                        "value": 0.55,
                        "weight": 50,
                    },
                ],
            },
        ]
    }


def test_make_characteristics_input():
    calculated_subcharacteristics = [
        {"key": "time_behaviour", "value": "0.8"},
        {"key": "resource_utilization", "value": 0.6},
    ]

    result = make_characteristics_input(calculated_subcharacteristics)

    assert result == {
        "characteristics": [
            {
                "key": "performance_efficiency",
                "subcharacteristics": [
                    {
                        "key": "time_behaviour",
                        "value": 0.8,
                        "weight": 50,
                    },
                    {
                        "key": "resource_utilization",
                        "value": 0.6,
                        "weight": 50,
                    },
                ],
            },
        ]
    }


def test_build_json_output():
    repository_name = (
        "fga-eps-mds-2023-2-MeasureSoftGram-CLI-01-05-2023-21-40-30-extracted.metrics"
    )
    calculated_measures = {
        "measures": [
            {"key": "response_time", "value": 0.9},
            {"key": "cpu_utilization", "value": 0.8},
            {"key": "memory_utilization", "value": 0.7},
        ]
    }
    calculated_subcharacteristics = {
        "subcharacteristics": [
            {"key": "time_behaviour", "value": 0.9},
            {"key": "resource_utilization", "value": 0.7516648189186454},
        ]
    }
    calculated_characteristics = {
        "characteristics": [
            {"key": "performance_efficiency", "value": 0.82915619758885},
        ]
    }

    result = build_json_output(
        repository_name,
        calculated_characteristics,
        calculated_subcharacteristics,
        calculated_measures,
    )

    assert result == {
        "repository": [
            {"key": "repository", "value": "fga-eps-mds-2023-2-MeasureSoftGram-CLI"}
        ],
        "version": [{"key": "version", "value": "01-05-2023-21-40"}],
        "measures": [
            {"key": "response_time", "value": 0.9},
            {"key": "cpu_utilization", "value": 0.8},
            {"key": "memory_utilization", "value": 0.7},
        ],
        "subcharacteristics": [
            {"key": "time_behaviour", "value": 0.9},
            {"key": "resource_utilization", "value": 0.7516648189186454},
        ],
        "characteristics": [
            {"key": "performance_efficiency", "value": 0.82915619758885},
        ],
    }


def test_calculate_perf_eff_measures():
    repository_name = "perf-eff-repo-12-11-2023-02-57-52-extracted.metrics"
    endpoint_calls = [[1, 2], [2, 1], [1, 2], [2, 1]]
    measures_input = {
        "measures": [
            {
                "key": "cpu_utilization",
                "releases": [
                    {
                        "metrics": [10.0, 10.0, 10.0, 10.0],
                        "endpoint_calls": endpoint_calls,
                    },
                    {
                        "metrics": [10.0, 10.0, 10.0, 10.0],
                        "endpoint_calls": endpoint_calls,
                    },
                ],
            },
            {
                "key": "memory_utilization",
                "releases": [
                    {
                        "metrics": [10.0, 10.0, 10.0, 10.0],
                        "endpoint_calls": endpoint_calls,
                    },
                    {
                        "metrics": [20.0, 20.0, 20.0, 20.0],
                        "endpoint_calls": endpoint_calls,
                    },
                ],
            },
            {
                "key": "response_time",
                "releases": [
                    {"metrics": [1.5, 1.5, 1.5, 1.5], "endpoint_calls": endpoint_calls},
                    {"metrics": [1.5, 1.5, 1.5, 1.5], "endpoint_calls": endpoint_calls},
                ],
            },
        ]
    }

    result = calculate_perf_eff_measures(repository_name, measures_input)

    assert result["repository"] == [{"key": "repository", "value": "perf-eff-repo"}]
    assert result["version"] == [{"key": "version", "value": "12-11-2023-02-57"}]

    measures = {m["key"]: m["value"] for m in result["measures"]}
    assert measures["response_time"] == pytest.approx(1.0)
    assert measures["cpu_utilization"] == pytest.approx(1.0)
    assert measures["memory_utilization"] == pytest.approx(0.0)

    subcharacteristics = {s["key"]: s["value"] for s in result["subcharacteristics"]}
    assert subcharacteristics["time_behaviour"] == pytest.approx(1.0)
    assert subcharacteristics["resource_utilization"] == pytest.approx(
        0.7071067811865475
    )

    characteristics = {c["key"]: c["value"] for c in result["characteristics"]}
    assert characteristics["performance_efficiency"] == pytest.approx(
        0.8660254037844386
    )


def test_calculate_perf_eff_measures_from_parsed_csv_data():
    measures_input = parse_performance_efficiency_data(
        Path("tests/unit/data/perf-eff-data-1.csv"),
        Path("tests/unit/data/perf-eff-data-2.csv"),
        "perf-eff-csv",
    )
    repository_name = "perf-eff-csv-28-07-2024-00-00-22-extracted.metrics"

    result = calculate_perf_eff_measures(repository_name, measures_input)

    assert result["repository"] == [{"key": "repository", "value": "perf-eff-csv"}]
    assert result["version"] == [{"key": "version", "value": "28-07-2024-00-00"}]
    assert [m["key"] for m in result["measures"]] == [
        "response_time",
        "cpu_utilization",
        "memory_utilization",
    ]
    for item in (
        result["measures"] + result["subcharacteristics"] + result["characteristics"]
    ):
        assert 0.0 <= item["value"] <= 1.0
