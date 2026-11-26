"""Avisos do msgram calculate sobre medidas não calculadas (DOC#301)."""

import copy
import json
import shutil
from pathlib import Path

from src.cli.commands.cmd_calculate import command_calculate
from src.cli.resources.metrics import QUALIFIERS_KEY
from staticfiles import DEFAULT_PRE_CONFIG as pre_config
from tests.unit.cli_output import normalize_cli_output

DATA = Path("tests/unit/data")
GITHUB_METRICS = "github_fga-eps-mds-2024.1-MeasureSoftGram-DOC-28-07-2024-00-00-22-extracted.metrics"
SUCCESS = "All calculations performed successfully!"
NO_GITHUB = "No GitHub metrics in the extracted files"
NO_SONAR = "No SonarQube metrics in the extracted files"


def _sonar_metrics():
    project = "org_repo"
    files = {
        f"{project}:src/a.py": ("FIL", "10", "5", "8.0", "20.0", "80.0", "0.0"),
        f"{project}:src/b.py": ("FIL", "4", "4", "0.0", "10.0", "100.0", "2.0"),
        f"{project}:tests/t1.py": ("UTS", None, None, "0.0", None, None, None),
        f"{project}:tests/t2.py": ("UTS", None, None, "0.0", None, None, None),
    }
    extracted = {
        project: [
            {"metric": "tests", "value": "12"},
            {"metric": "test_errors", "value": "0"},
            {"metric": "test_failures", "value": "0"},
            {"metric": "ncloc", "value": "100"},
        ],
        QUALIFIERS_KEY: {project: "TRK"},
    }
    names = (
        "complexity",
        "functions",
        "sqale_debt_ratio",
        "comment_lines_density",
        "coverage",
        "duplicated_lines_density",
    )
    for key, (qualifier, *values) in files.items():
        extracted[QUALIFIERS_KEY][key] = qualifier
        measures = [
            {"metric": name, "value": value}
            for name, value in zip(names, values)
            if value is not None
        ]
        if qualifier == "FIL":
            measures.append({"metric": "ncloc", "value": "50"})
        else:
            measures += [
                {"metric": "tests", "value": "6"},
                {"metric": "test_execution_time", "value": "100"},
            ]
        extracted[key] = measures
    return extracted


def _sonar_only_config():
    config = copy.deepcopy(pre_config)
    config["characteristics"] = [
        c for c in config["characteristics"] if c["key"] != "functional_suitability"
    ]
    for characteristic in config["characteristics"]:
        characteristic["subcharacteristics"] = [
            s for s in characteristic["subcharacteristics"] if s["key"] != "maturity"
        ]
        characteristic["weight"] = 50
        for subcharacteristic in characteristic["subcharacteristics"]:
            subcharacteristic["weight"] = 100
    return config


def _run(tmp_path, capsys, config, metrics_files):
    config_dir = tmp_path / "config"
    extracted_dir = tmp_path / "extracted"
    config_dir.mkdir()
    extracted_dir.mkdir()
    (config_dir / "msgram.json").write_text(json.dumps(config))
    for name, content in metrics_files.items():
        if isinstance(content, Path):
            shutil.copy(content, extracted_dir / name)
        else:
            (extracted_dir / name).write_text(json.dumps(content))

    command_calculate(
        {
            "output_format": "tabular",
            "config_path": config_dir,
            "extracted_path": extracted_dir,
        }
    )
    return normalize_cli_output(capsys.readouterr().out)


def test_warns_measures_without_source_data(tmp_path, capsys):
    out = _run(
        tmp_path,
        capsys,
        pre_config,
        {"org-repo-11-11-2026-10-00-00-develop-extracted.metrics": _sonar_metrics()},
    )

    assert out.count(NO_GITHUB) == 1
    assert "team_throughput" in out
    assert "ci_feedback_time" in out
    assert SUCCESS not in out
    assert "Calculations finished with 1 warning(s)" in out


def test_no_warning_when_every_source_has_a_file(tmp_path, capsys):
    out = _run(
        tmp_path,
        capsys,
        pre_config,
        {
            "org-repo-11-11-2026-10-00-00-develop-extracted.metrics": _sonar_metrics(),
            GITHUB_METRICS: DATA / GITHUB_METRICS,
        },
    )

    assert NO_GITHUB not in out
    assert NO_SONAR not in out


def test_success_message_without_warnings(tmp_path, capsys):
    out = _run(
        tmp_path,
        capsys,
        _sonar_only_config(),
        {"org-repo-11-11-2026-10-00-00-develop-extracted.metrics": _sonar_metrics()},
    )

    assert SUCCESS in out
    assert "warning(s)" not in out


def test_missing_metric_warning_is_counted(tmp_path, capsys):
    metrics = _sonar_metrics()
    for key, measures in metrics.items():
        if key != QUALIFIERS_KEY:
            metrics[key] = [m for m in measures if m["metric"] != "sqale_debt_ratio"]

    out = _run(
        tmp_path,
        capsys,
        _sonar_only_config(),
        {"org-repo-11-11-2026-10-00-00-develop-extracted.metrics": metrics},
    )

    assert "Measure 'technical_debt_ratio' could not be calculated" in out
    assert SUCCESS not in out
    assert "Calculations finished with 1 warning(s)" in out
