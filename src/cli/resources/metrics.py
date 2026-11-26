"""Seleção dos valores das métricas extraídas para o cálculo das medidas.

Segue a mesma regra do Service (``math_model/services.py``):

- métricas por arquivo (``FILE_METRICS``): um valor por componente ``FIL``,
  sem os arquivos vazios (``ncloc = 0``);
- métricas de teste (``UTS_METRICS``): um valor por componente ``UTS``;
- demais métricas do SonarQube: o valor do projeto (``TRK``).

O ``msgram extract`` registra o qualifier de cada componente em
``QUALIFIERS_KEY``. Arquivos extraídos por versões antigas não têm esse
registro e continuam sendo lidos como antes (todos os componentes).
"""

QUALIFIERS_KEY = "__qualifiers__"

FILE_METRICS = (
    "coverage",
    "complexity",
    "functions",
    "comment_lines_density",
    "duplicated_lines_density",
    "sqale_debt_ratio",
)

UTS_METRICS = ("test_execution_time", "tests")

GITHUB_LISTED_METRICS = (
    "resolved_issues",
    "total_issues",
    "sum_ci_feedback_times",
    "total_builds",
)


def has_qualifiers(extracted):
    return isinstance(extracted.get(QUALIFIERS_KEY), dict)


def iter_components(extracted):
    """Gera (chave, qualifier, {métrica: valor}) para cada componente extraído."""
    qualifiers = extracted.get(QUALIFIERS_KEY) or {}
    for key, measures in extracted.items():
        if key == QUALIFIERS_KEY or not isinstance(measures, list):
            continue
        values = {
            measure.get("metric"): measure.get("value")
            for measure in measures
            if isinstance(measure, dict)
        }
        yield key, qualifiers.get(key), values


def _is_empty_file(values):
    try:
        return float(values.get("ncloc")) == 0
    except (TypeError, ValueError):
        return False


def _source_files(extracted):
    return [
        values
        for _, qualifier, values in iter_components(extracted)
        if qualifier == "FIL" and not _is_empty_file(values)
    ]


def get_file_metric_values(extracted, metric_keys):
    """Valores por arquivo alinhados entre as métricas informadas.

    O msgram-core pareia as listas pela posição (ex.: ``complexity[i]`` com
    ``functions[i]``), então só entram os arquivos que têm todas as métricas.
    """
    files = [
        values
        for values in _source_files(extracted)
        if all(values.get(metric) is not None for metric in metric_keys)
    ]
    return {metric: [values[metric] for values in files] for metric in metric_keys}


def _legacy_metric_value(extracted):
    response_data = {}
    listed = FILE_METRICS + UTS_METRICS + GITHUB_LISTED_METRICS
    for _, _, values in iter_components(extracted):
        for metric_name, metric_value in values.items():
            if metric_name in listed:
                response_data.setdefault(metric_name, []).append(metric_value)
            else:
                response_data[metric_name] = metric_value
    return response_data


def _add_component_value(response_data, qualifier, metric_name, metric_value):
    if metric_name in UTS_METRICS:
        if qualifier == "UTS":
            response_data.setdefault(metric_name, []).append(metric_value)
    elif metric_name in GITHUB_LISTED_METRICS:
        response_data.setdefault(metric_name, []).append(metric_value)
    elif qualifier == "TRK" or metric_name not in response_data:
        response_data[metric_name] = metric_value


def get_metric_value(extracted):
    """Recupera os valores das métricas no formato esperado pelo cálculo."""
    if not has_qualifiers(extracted):
        return _legacy_metric_value(extracted)

    files = _source_files(extracted)
    response_data = {}
    for metric_name in FILE_METRICS:
        metric_values = [
            values[metric_name]
            for values in files
            if values.get(metric_name) is not None
        ]
        if metric_values:
            response_data[metric_name] = metric_values

    for _, qualifier, values in iter_components(extracted):
        for metric_name, metric_value in values.items():
            if metric_name not in FILE_METRICS:
                _add_component_value(
                    response_data, qualifier, metric_name, metric_value
                )
    return response_data
