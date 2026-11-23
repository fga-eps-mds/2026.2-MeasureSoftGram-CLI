"""Validação dos pesos do msgram.json (DOC#302).

Em cada grupo (as características, as subcaracterísticas de uma característica
e as medidas de uma subcaracterística) os pesos devem somar 100, como no
arquivo gerado pelo msgram init e como o Service exige. O Core agrega pela
norma ponderada, então uma soma diferente não quebra o cálculo, mas os pesos
deixam de significar porcentagens. Por decisão do PO, isso é erro: o
calculate não calcula e o list termina com código diferente de zero.
"""

import math
from numbers import Real

from src.cli.resources.weight_groups import list_groups
from src.cli.utils import print_error, print_output

EXPECTED_SUM = 100
MIN_WEIGHT = 0
MAX_WEIGHT = 100
SUM_TOLERANCE = 1e-9


def _is_valid_weight(value) -> bool:
    return (
        isinstance(value, Real)
        and not isinstance(value, bool)
        and math.isfinite(value)
        and MIN_WEIGHT <= value <= MAX_WEIGHT
    )


def _format_number(value) -> str:
    return f"{value:g}"


def _format_value(value) -> str:
    if value is None:
        return "ausente"
    if isinstance(value, str):
        return f'"{value}"'
    return str(value)


def validate_weights(config: dict) -> list:
    """Devolve a lista de problemas de peso de todos os grupos do config.

    Um grupo com algum peso inválido (ausente, não numérico ou fora de 0 a 100)
    tem o peso apontado e não tem a soma conferida. Grupos vazios são ignorados.
    """
    errors = []
    for group in list_groups(config):
        if not group.entities:
            continue

        invalid = [
            (entity, group.weights.get(entity))
            for entity in group.entities
            if not _is_valid_weight(group.weights.get(entity))
        ]
        if invalid:
            errors.extend(
                f"{group.label}: o peso de {entity} é {_format_value(value)} "
                f"(esperado um número entre {MIN_WEIGHT} e {MAX_WEIGHT})"
                for entity, value in invalid
            )
            continue

        total = sum(group.weights[entity] for entity in group.entities)
        if not math.isclose(total, EXPECTED_SUM, abs_tol=SUM_TOLERANCE):
            errors.append(
                f"{group.label}: a soma é {_format_number(total)} "
                f"(esperado {EXPECTED_SUM})"
            )
    return errors


def format_weight_errors(errors: list, config_file) -> list:
    """Linhas da mensagem de erro, no formato do protótipo da DOC#302."""
    return (
        [f"Pesos inválidos em {config_file}"]
        + [f"  • {error}" for error in errors]
        + ["  Corrija o arquivo ou use: msgram weights"]
    )


def print_weight_errors(errors: list, config_file) -> None:
    first, *rest = format_weight_errors(errors, config_file)
    print_error(first)
    for line in rest:
        print_output(line, "error")
