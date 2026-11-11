"""Aviso sobre medidas que dependem de dados do GitHub (DOC#155, DOC#301).

O dataset de exemplo só tem métricas do SonarQube. Sem o aviso, as medidas
do GitHub configuradas no msgram.json (e as características que dependem só
delas) somem do resultado sem nenhuma explicação. O aviso vem do calculate,
que vale para a demo e para qualquer outro uso da CLI.
"""

import copy
import json

from src.cli.commands.cmd_demo import command_demo
from tests.unit.cli_output import normalize_cli_output
from staticfiles import DEFAULT_PRE_CONFIG as pre_config

GITHUB_MEASURES = ("team_throughput", "ci_feedback_time")
WARNING = "No GitHub metrics in the extracted files"


def _sonar_only_config():
    config = copy.deepcopy(pre_config)
    config["characteristics"] = [
        c for c in config["characteristics"] if c["key"] == "maintainability"
    ]
    config["characteristics"][0]["weight"] = 100
    return config


def test_demo_warns_about_github_measures(tmp_path, capsys):
    command_demo({"output_path": tmp_path / "demo", "output_format": "json"})

    out = normalize_cli_output(capsys.readouterr().out)
    assert out.count(WARNING) == 1
    for measure in GITHUB_MEASURES:
        assert measure in out
    assert "All calculations performed successfully!" not in out
    assert "warning(s)" in out


def test_demo_does_not_warn_without_github_measures(tmp_path, capsys):
    output_path = tmp_path / "demo"
    output_path.mkdir()
    (output_path / "msgram.json").write_text(json.dumps(_sonar_only_config()))

    command_demo({"output_path": output_path, "output_format": "json"})

    out = normalize_cli_output(capsys.readouterr().out)
    assert WARNING not in out
    assert "Demo finished successfully!" in out
