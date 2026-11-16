"""Seleção dos valores por tipo de componente do SonarQube (DOC#300).

A CLI precisa usar os mesmos valores que o Service: métricas por arquivo só dos
componentes FIL não vazios, métricas de teste dos UTS e o resto do TRK.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from src.cli.commands.cmd_calculate import calculate_all
from src.cli.commands.cmd_extract import component_qualifiers, extract_sonar
from src.cli.resources.measure import calculate_measures, is_legacy_sonar_extraction
from src.cli.resources.metrics import (
    QUALIFIERS_KEY,
    get_file_metric_values,
    get_metric_value,
)
from genericparser import GenericParser
from resources import calculate_measures as core_calculate
from staticfiles import DEFAULT_PRE_CONFIG as pre_config

PROJECT = "org_repo"


def _measures(**metrics):
    return [{"metric": key, "value": value} for key, value in metrics.items()]


def _extracted():
    return {
        PROJECT: _measures(
            sqale_debt_ratio="0.1",
            coverage="90.0",
            complexity="100",
            functions="50",
            tests="10",
            test_failures="0",
            test_errors="0",
            ncloc="1000",
        ),
        f"{PROJECT}:src/a.py": _measures(
            sqale_debt_ratio="10.0", complexity="10", functions="5", ncloc="100"
        ),
        f"{PROJECT}:src/b.py": _measures(
            sqale_debt_ratio="0.0", complexity="4", functions="4", ncloc="40"
        ),
        # arquivo sem funções: fica fora do par complexity × functions
        f"{PROJECT}:src/c.py": _measures(
            sqale_debt_ratio="20.0", complexity="2", ncloc="20"
        ),
        # arquivo vazio: fica fora de todas as métricas por arquivo
        f"{PROJECT}:src/__init__.py": _measures(
            sqale_debt_ratio="0.0", complexity="0", functions="0", ncloc="0"
        ),
        f"{PROJECT}:tests/test_a.py": _measures(
            sqale_debt_ratio="0.0", tests="7", test_execution_time="30"
        ),
        f"{PROJECT}:tests/test_b.py": _measures(
            sqale_debt_ratio="0.0", tests="3", test_execution_time="10"
        ),
        QUALIFIERS_KEY: {
            PROJECT: "TRK",
            f"{PROJECT}:src/a.py": "FIL",
            f"{PROJECT}:src/b.py": "FIL",
            f"{PROJECT}:src/c.py": "FIL",
            f"{PROJECT}:src/__init__.py": "FIL",
            f"{PROJECT}:tests/test_a.py": "UTS",
            f"{PROJECT}:tests/test_b.py": "UTS",
        },
    }


def test_file_metrics_use_only_non_empty_fil_components():
    values = get_metric_value(_extracted())

    assert values["sqale_debt_ratio"] == ["10.0", "0.0", "20.0"]
    assert values["complexity"] == ["10", "4", "2"]
    assert values["functions"] == ["5", "4"]


def test_test_metrics_use_only_uts_components():
    values = get_metric_value(_extracted())

    assert values["tests"] == ["7", "3"]
    assert values["test_execution_time"] == ["30", "10"]


def test_project_metrics_use_the_trk_component():
    extracted = _extracted()
    # o TRK vem antes do arquivo, mas o valor do projeto continua valendo
    extracted[f"{PROJECT}:src/a.py"].append({"metric": "test_failures", "value": "3"})

    values = get_metric_value(extracted)

    assert values["test_failures"] == "0"
    assert values["ncloc"] == "1000"


def test_file_metric_values_are_aligned_by_file():
    aligned = get_file_metric_values(_extracted(), ["complexity", "functions"])

    assert aligned == {"complexity": ["10", "4"], "functions": ["5", "4"]}


def test_technical_debt_ratio_matches_the_service_rule():
    infos, _ = calculate_measures(_extracted(), pre_config)

    measures = {m["key"]: m["value"] for m in infos["measures"]}
    # (1 - 10/20) + (1 - 0/20) + 0 (ratio >= 20), média de 3 arquivos
    assert measures["technical_debt_ratio"] == pytest.approx(0.5)


def test_non_complex_file_density_uses_only_files_with_both_metrics():
    infos, _ = calculate_measures(_extracted(), pre_config)
    expected = core_calculate(
        {
            "measures": [
                {
                    "key": "non_complex_file_density",
                    "metrics": [
                        {"key": "complexity", "value": [10.0, 4.0]},
                        {"key": "functions", "value": [5.0, 4.0]},
                    ],
                }
            ]
        }
    )["measures"][0]["value"]

    measures = {m["key"]: m["value"] for m in infos["measures"]}
    assert measures["non_complex_file_density"] == pytest.approx(expected)


@patch("src.cli.resources.measure.print_warn")
def test_core_error_in_one_measure_does_not_stop_the_others(mock_print_warn):
    extracted = _extracted()
    del extracted[f"{PROJECT}:tests/test_b.py"]
    del extracted[QUALIFIERS_KEY][f"{PROJECT}:tests/test_b.py"]

    infos, _ = calculate_measures(extracted, pre_config)

    # com um único UTS o msgram-core recebe "tests" como número e recusa
    measure_keys = [m["key"] for m in infos["measures"]]
    assert "passed_tests" not in measure_keys
    assert "technical_debt_ratio" in measure_keys
    warnings = [call.args[0] for call in mock_print_warn.call_args_list]
    assert any("'passed_tests' could not be calculated" in w for w in warnings)


def test_legacy_extraction_keeps_previous_behavior():
    extracted = _extracted()
    del extracted[QUALIFIERS_KEY]

    values = get_metric_value(extracted)

    assert is_legacy_sonar_extraction(extracted)
    assert len(values["sqale_debt_ratio"]) == 7


def test_github_extraction_is_not_legacy_sonar():
    extracted = {"org/repo": _measures(resolved_issues=1.0, total_issues=6.0)}

    assert not is_legacy_sonar_extraction(extracted)


@patch("src.cli.commands.cmd_calculate.print_warn")
def test_calculate_warns_legacy_extraction(mock_print_warn):
    extracted = _extracted()
    del extracted[QUALIFIERS_KEY]

    calculate_all(extracted, "legacy-extracted.metrics", pre_config)

    warning = mock_print_warn.call_args_list[0].args[0]
    assert "legacy-extracted.metrics" in warning
    assert "msgram extract" in warning


@patch("src.cli.commands.cmd_calculate.print_warn")
def test_calculate_does_not_warn_current_extraction(mock_print_warn):
    calculate_all(_extracted(), "current-extracted.metrics", pre_config)

    assert not any(
        "component types" in call.args[0] for call in mock_print_warn.call_args_list
    )


def test_component_qualifiers():
    components = [
        {"key": f"{PROJECT}:src/a.py", "qualifier": "FIL"},
        {"key": f"{PROJECT}:tests/t.py", "qualifier": "UTS"},
        {"key": PROJECT, "qualifier": "TRK"},
    ]

    assert component_qualifiers(components) == {
        f"{PROJECT}:src/a.py": "FIL",
        f"{PROJECT}:tests/t.py": "UTS",
        PROJECT: "TRK",
    }


def test_extract_sonar_records_qualifiers(tmp_path):
    raw = tmp_path / "raw"
    extracted = tmp_path / "extracted"
    raw.mkdir()
    extracted.mkdir()
    sample = Path(
        "tests/unit/data/fga-eps-mds-2022-2-MeasureSoftGram-CLI-01-11-2023-21-59-03-develop.json"
    )
    (raw / sample.name).write_text(sample.read_text())

    extract_sonar(extracted, raw, GenericParser())

    (metrics_file,) = extracted.glob("*.metrics")
    result = json.loads(metrics_file.read_text())
    qualifiers = result[QUALIFIERS_KEY]
    raw_json = json.loads(sample.read_text())
    assert qualifiers[raw_json["baseComponent"]["key"]] == "TRK"
    assert {qualifiers[c["key"]] for c in raw_json["components"]} == {
        c["qualifier"] for c in raw_json["components"]
    }
