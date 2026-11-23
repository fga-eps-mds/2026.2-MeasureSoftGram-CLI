"""Validação dos pesos do msgram.json (DOC#302)."""

import copy
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from src.cli.commands.cmd_calculate import command_calculate
from src.cli.commands.cmd_list import command_list
from src.cli.resources.weights import format_weight_errors, validate_weights
from staticfiles import DEFAULT_PRE_CONFIG as pre_config
from tests.unit.cli_output import normalize_cli_output

MODIFIABILITY = "maintainability › modifiability › medidas"
EXTRACTED = Path(
    "tests/unit/data/"
    "fga-eps-mds-2022-2-MeasureSoftGram-CLI-01-05-2023-21-40-30-develop-extracted.metrics"
)


def _set_measure_weight(config, key, weight):
    for characteristic in config["characteristics"]:
        for subcharacteristic in characteristic["subcharacteristics"]:
            for measure in subcharacteristic["measures"]:
                if measure["key"] == key:
                    measure["weight"] = weight
    return config


def _config_with_debt_weight(weight):
    return _set_measure_weight(
        copy.deepcopy(pre_config), "technical_debt_ratio", weight
    )


def _flat_config(*weights):
    return {
        "characteristics": [
            {"key": f"c{i}", "weight": weight, "subcharacteristics": []}
            for i, weight in enumerate(weights)
        ]
    }


def test_default_config_is_valid():
    assert validate_weights(pre_config) == []


def test_measure_group_that_does_not_sum_100():
    assert validate_weights(_config_with_debt_weight(30)) == [
        f"{MODIFIABILITY}: a soma é 105 (esperado 100)"
    ]


def test_lists_every_invalid_group_at_once():
    config = _config_with_debt_weight(30)
    first = config["characteristics"][0]
    first["weight"] += 7
    first["subcharacteristics"][0]["weight"] += 1

    errors = validate_weights(config)

    assert errors == [
        "Características: a soma é 107 (esperado 100)",
        f"{first['key']} › subcaracterísticas: a soma é 101 (esperado 100)",
        f"{MODIFIABILITY}: a soma é 105 (esperado 100)",
    ]


@pytest.mark.parametrize(
    "value, shown",
    [("abc", '"abc"'), (None, "ausente"), (-5, "-5"), (120, "120"), (True, "True")],
)
def test_invalid_weight_value_names_entity_and_value(value, shown):
    config = _set_measure_weight(
        copy.deepcopy(pre_config), "commented_file_density", value
    )
    if value is None:
        _remove_weight(config, "commented_file_density")

    assert validate_weights(config) == [
        f"{MODIFIABILITY}: o peso de commented_file_density é {shown} "
        "(esperado um número entre 0 e 100)"
    ]


def _remove_weight(config, key):
    for characteristic in config["characteristics"]:
        for subcharacteristic in characteristic["subcharacteristics"]:
            for measure in subcharacteristic["measures"]:
                if measure["key"] == key:
                    del measure["weight"]


def test_decimal_weights_that_sum_100_are_accepted():
    assert validate_weights(_flat_config(33.3, 33.3, 33.4)) == []


def test_decimal_weights_that_do_not_sum_100_are_rejected():
    assert validate_weights(_flat_config(33.33, 33.33, 33.33)) == [
        "Características: a soma é 99.99 (esperado 100)"
    ]


def test_single_entity_group_must_weigh_100():
    assert validate_weights(_flat_config(100)) == []
    assert validate_weights(_flat_config(90)) == [
        "Características: a soma é 90 (esperado 100)"
    ]


def test_format_weight_errors():
    assert format_weight_errors(["x: a soma é 90 (esperado 100)"], "a/msgram.json") == [
        "Pesos inválidos em a/msgram.json",
        "  • x: a soma é 90 (esperado 100)",
        "  Corrija o arquivo ou use: msgram weights",
    ]


@patch("src.cli.commands.cmd_list.clear_console")
def test_list_shows_config_then_error_and_exits_1(mock_clear, tmp_path, capsys):
    (tmp_path / "msgram.json").write_text(json.dumps(_config_with_debt_weight(30)))

    with pytest.raises(SystemExit) as exit_info:
        command_list({"config_path": tmp_path})

    assert exit_info.value.code == 1
    out = normalize_cli_output(capsys.readouterr().out)
    assert "technical_debt_ratio" in out
    assert out.index("technical_debt_ratio") < out.index("Pesos inválidos em")
    assert f"{MODIFIABILITY}: a soma é 105 (esperado 100)" in out
    assert "Corrija o arquivo ou use: msgram weights" in out


@patch("src.cli.commands.cmd_list.clear_console")
def test_list_with_valid_weights_does_not_exit(mock_clear, tmp_path, capsys):
    (tmp_path / "msgram.json").write_text(json.dumps(pre_config))

    command_list({"config_path": tmp_path})

    assert "Pesos inválidos" not in capsys.readouterr().out


def test_calculate_stops_before_calculating(tmp_path, capsys):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "msgram.json").write_text(json.dumps(_config_with_debt_weight(30)))

    with pytest.raises(SystemExit) as exit_info:
        command_calculate(
            {
                "output_format": "tabular",
                "config_path": config_dir,
                "extracted_path": EXTRACTED,
            }
        )

    assert exit_info.value.code == 1
    out = normalize_cli_output(capsys.readouterr().out)
    assert f"{MODIFIABILITY}: a soma é 105 (esperado 100)" in out
    assert "Reading extracted files" not in out
    assert "TSQMI" not in out
