"""Aviso de pesos que não somam 100 no msgram.json (DOC#302)."""

import copy
import json
from pathlib import Path
from unittest.mock import patch

from src.cli.commands.cmd_calculate import command_calculate
from src.cli.commands.cmd_list import command_list
from src.cli.resources.weights import get_weight_sum_problems, weight_sum_warnings
from staticfiles import DEFAULT_PRE_CONFIG as pre_config
from tests.unit.cli_output import normalize_cli_output

MODIFIABILITY = "maintainability > modifiability measures"


def _config_with_debt_weight(weight):
    config = copy.deepcopy(pre_config)
    for characteristic in config["characteristics"]:
        for subcharacteristic in characteristic["subcharacteristics"]:
            for measure in subcharacteristic["measures"]:
                if measure["key"] == "technical_debt_ratio":
                    measure["weight"] = weight
    return config


def test_default_config_has_no_problems():
    assert get_weight_sum_problems(pre_config) == []


def test_measure_group_that_does_not_sum_100():
    assert get_weight_sum_problems(_config_with_debt_weight(30)) == [
        (MODIFIABILITY, 105)
    ]
    assert weight_sum_warnings(_config_with_debt_weight(30)) == [
        f"Weights of {MODIFIABILITY} sum to 105 (expected 100)."
    ]


def test_characteristic_and_subcharacteristic_groups():
    config = copy.deepcopy(pre_config)
    config["characteristics"][0]["weight"] = 50
    config["characteristics"][0]["subcharacteristics"][0]["weight"] = 10

    groups = [group for group, _ in get_weight_sum_problems(config)]

    assert groups == [
        "characteristics",
        f"{config['characteristics'][0]['key']} subcharacteristics",
    ]


def test_decimal_weights_within_tolerance():
    config = {
        "characteristics": [
            {"key": key, "weight": 33.33, "subcharacteristics": []}
            for key in ("a", "b", "c")
        ]
    }

    assert get_weight_sum_problems(config) == []


@patch("src.cli.commands.cmd_list.clear_console")
def test_list_warns_weights(mock_clear, tmp_path, capsys):
    (tmp_path / "msgram.json").write_text(json.dumps(_config_with_debt_weight(30)))

    command_list({"config_path": tmp_path})

    out = normalize_cli_output(capsys.readouterr().out)
    assert f"Weights of {MODIFIABILITY} sum to 105" in out


def test_calculate_warns_weights_without_blocking(tmp_path, capsys):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "msgram.json").write_text(json.dumps(_config_with_debt_weight(30)))
    extracted = Path(
        "tests/unit/data/"
        "fga-eps-mds-2022-2-MeasureSoftGram-CLI-01-05-2023-21-40-30-develop-extracted.metrics"
    )

    command_calculate(
        {
            "output_format": "tabular",
            "config_path": config_dir,
            "extracted_path": extracted,
        }
    )

    out = normalize_cli_output(capsys.readouterr().out)
    assert f"Weights of {MODIFIABILITY} sum to 105" in out
    assert "TSQMI" in out
    assert "All calculations performed successfully!" not in out
