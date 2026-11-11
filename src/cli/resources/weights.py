"""Validação dos pesos do msgram.json.

Em cada grupo (as características, as subcaracterísticas de uma característica
e as medidas de uma subcaracterística) os pesos devem somar 100, como no
arquivo gerado pelo msgram init. O Core agrega pela norma ponderada, então uma
soma diferente não impede o cálculo, mas quase sempre é erro de edição.
"""

EXPECTED_SUM = 100
# pesos com casas decimais, como 33,33 x 3, somam 99,99
TOLERANCE = 0.1


def _weight_sum(items):
    return sum(item.get("weight", 0) for item in items)


def _weight_groups(config):
    characteristics = config.get("characteristics", [])
    yield "characteristics", characteristics
    for characteristic in characteristics:
        subcharacteristics = characteristic.get("subcharacteristics", [])
        yield f"{characteristic.get('key')} subcharacteristics", subcharacteristics
        for subcharacteristic in subcharacteristics:
            yield (
                f"{characteristic.get('key')} > {subcharacteristic.get('key')} measures",
                subcharacteristic.get("measures", []),
            )


def get_weight_sum_problems(config):
    """Retorna [(grupo, soma)] dos grupos cujos pesos não somam 100."""
    return [
        (group, total)
        for group, items in _weight_groups(config)
        if items and abs((total := _weight_sum(items)) - EXPECTED_SUM) > TOLERANCE
    ]


def weight_sum_warnings(config):
    return [
        f"Weights of {group} sum to {total:g} (expected {EXPECTED_SUM})."
        for group, total in get_weight_sum_problems(config)
    ]
