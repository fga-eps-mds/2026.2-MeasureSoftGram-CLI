"""msgram weights: define os pesos do msgram.json por comparação par a par (AHP).

O cálculo (prioridades e CR) vem do módulo core.ahp, que usa a AHPy. Este
comando só faz as perguntas, mostra o resumo e grava o campo weight depois
da confirmação. Nenhum arquivo novo é criado.
"""

import json
import os
import sys
import tempfile
from pathlib import Path

from core.ahp import (
    CR_THRESHOLD,
    calculate_group,
    most_inconsistent,
    pairs,
)
from rich.prompt import Prompt
from rich.text import Text

from src.cli.i18n import _, format_decimal, ngettext
from src.cli.resources.weight_groups import (
    InvalidGroupPath,
    apply_weights,
    find_group,
    list_groups,
)
from src.cli.utils import console, print_error, print_info, print_output, print_rule
from src.config.settings import FILE_CONFIG

INTENSITIES = ["moderadamente", "fortemente", "muito_fortemente", "extremamente"]


def intensity_options() -> str:
    return _("[1] moderately  [2] strongly  [3] very strongly  [4] extremely")


def saaty_phrase(intensity: str) -> str:
    return {
        "moderadamente": _("moderately more important"),
        "fortemente": _("strongly more important"),
        "muito_fortemente": _("very strongly more important"),
        "extremamente": _("extremely more important"),
    }[intensity]


class Cancelled(Exception):
    pass


class ChoicePrompt(Prompt):
    @property
    def illegal_choice_message(self) -> str:
        return "[prompt.invalid.choice]" + _("Choose one of the options shown")


# ------------------------------------------------------------------ entrada


def ask_choice(prompt: str, choices, default=None) -> str:
    """Pergunta no terminal e devolve uma das opções. Isolada para os testes."""
    try:
        return ChoicePrompt.ask(
            Text(prompt),
            choices=list(choices),
            default=default,
            show_choices=False,
            show_default=False,
            console=console,
        )
    except EOFError:
        # sem terminal (stdin fechado, CI, pipe): trata como cancelamento
        raise Cancelled()


def ask_pair(a: str, b: str):
    which = ask_choice(
        _("  Which is more important? [1] {a}  [2] {b}  [3] equally").format(a=a, b=b),
        ["1", "2", "3"],
    )
    if which == "3":
        return (a, b, None, "igual")
    preferred = a if which == "1" else b
    how = ask_choice(
        _("  How much more important? {options}").format(options=intensity_options()),
        ["1", "2", "3", "4"],
    )
    return (a, b, preferred, INTENSITIES[int(how) - 1])


# ------------------------------------------------------------------ formatação


def format_cr(cr) -> str:
    return format_decimal(cr)


def describe_answer(answer) -> str:
    a, b, preferred, intensity = answer
    if preferred is None:
        return _("{a} × {b}: equally important").format(a=a, b=b)
    return _("{a} × {b}: {preferred} is {phrase}").format(
        a=a, b=b, preferred=preferred, phrase=saaty_phrase(intensity)
    )


def describe_suggestion(answer) -> str:
    _first, _second, preferred, intensity = answer
    if preferred is None:
        return _("equally important")
    return _("{preferred} is {phrase}").format(
        preferred=preferred, phrase=saaty_phrase(intensity)
    )


def describe_cr(result) -> str:
    if result.consistency_ratio is None:
        return _("CR does not apply")
    if result.consistent:
        return f"CR {format_cr(result.consistency_ratio)}"
    limit = format_cr(CR_THRESHOLD)
    return _("⚠ CR {value}, above {limit}, accepted").format(
        value=format_cr(result.consistency_ratio), limit=limit
    )


# ------------------------------------------------------------------ grupos


def ask_group(group, title: str):
    """Faz as perguntas de um grupo até o usuário ter um resultado consistente ou aceitar."""
    group_pairs = pairs(group.entities)
    n = len(group_pairs)
    while True:
        console.line()
        print_output(
            ngettext(
                "[{title}] {label} ({n} comparison)",
                "[{title}] {label} ({n} comparisons)",
                n,
            ).format(title=title, label=group.label, n=n),
            "accent",
        )
        answers = []
        for i, (a, b) in enumerate(group_pairs, start=1):
            print_output(f"({i}/{n}) {a} × {b}")
            answers.append(ask_pair(a, b))

        result = calculate_group(group.entities, answers)

        if result.consistency_ratio is None:
            print_output(
                _("  Consistency: does not apply ({n} entities)").format(
                    n=len(group.entities)
                ),
                "muted",
            )
            return answers, result
        if result.consistent:
            print_output(
                _("  ✔ Consistency: CR = {value}").format(
                    value=format_cr(result.consistency_ratio)
                ),
                "success",
            )
            return answers, result

        print_output(
            _("  ⚠ Consistency: CR = {value} (above {limit})").format(
                value=format_cr(result.consistency_ratio),
                limit=format_cr(CR_THRESHOLD),
            ),
            "warning",
        )
        print_output(_("    Your answers contradict each other."), "warning")
        conflict = most_inconsistent(group.entities, answers, result)
        if conflict:
            print_output(
                _(
                    "    Most likely conflict: {a} × {b}. Suggestion: {suggestion}"
                ).format(
                    a=conflict.a,
                    b=conflict.b,
                    suggestion=describe_suggestion(conflict.suggested),
                ),
                "warning",
            )
        if (
            ask_choice(_("    [1] redo the group  [2] accept anyway"), ["1", "2"])
            == "2"
        ):
            return answers, result


def print_summary(entries, partial: bool):
    console.line()
    print_rule(_("Summary"))
    for group, answers, result in entries:
        print_output(f"{group.label} ({describe_cr(result)})", "accent")
        for answer in answers:
            print_output(f"  {describe_answer(answer)}")
        print_output(f"{'':33}" + _("before → after"), "muted")
        for entity in group.entities:
            before = group.weights.get(entity)
            before = "-" if before is None else before
            print_output(f"  {entity:<30} {before:>3} → {result.weights[entity]}")
        console.line()
    if partial:
        print_info(_("The other groups were not changed."))


# ------------------------------------------------------------------ arquivo


def save_config(file_path: Path, config: dict):
    """Grava num arquivo temporário e renomeia: uma falha no meio não corrompe o msgram.json."""
    fd, tmp = tempfile.mkstemp(dir=file_path.parent, prefix=".msgram-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(json.dumps(config, indent=4))
        os.replace(tmp, file_path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def display_path(file_path: Path) -> str:
    try:
        return os.path.relpath(file_path)
    except ValueError:
        return str(file_path)


# ------------------------------------------------------------------ comando


def load_config(file_path: Path, shown_path: str) -> dict:
    """Lê o msgram.json ou encerra com a orientação do Cenário 6."""
    if not file_path.exists():
        print_error(_("No configuration file found at {path}").format(path=shown_path))
        print_output(_("  Run the msgram init command"))
        sys.exit(1)
    try:
        return json.loads(file_path.read_text())
    except json.JSONDecodeError as e:
        print_error(
            _("The file {path} is not valid JSON: {error}").format(
                path=shown_path, error=e
            )
        )
        sys.exit(1)


def select_groups(config: dict, group_path):
    """Todos os grupos do arquivo ou só o informado em --group."""
    groups = list_groups(config)
    if not group_path:
        return groups
    try:
        return [find_group(groups, group_path)]
    except InvalidGroupPath as e:
        print_error(_("Group does not exist: {path}").format(path=e.path))
        print_output(_("  Valid paths:"))
        for path in e.valid_paths:
            print_output(f"    {path}")
        sys.exit(1)


def print_header(groups):
    to_ask = [g for g in groups if len(g.entities) > 1]
    singles = len(groups) - len(to_ask)
    total = sum(g.comparisons for g in groups)
    print_output(_("Weight definition by pairwise comparison"))
    print_output(
        _(
            "{groups} groups in the model · {total} comparisons · "
            "{singles} groups with a single entity (weight 100, no questions)"
        ).format(groups=len(groups), total=total, singles=singles),
        "muted",
    )


def confirm_save(shown_path: str) -> bool:
    yes = _("y")
    try:
        answer = ask_choice(
            _("Save the new weights to {path}? [y/N]").format(path=shown_path),
            [yes, "n"],
            default="n",
        )
    except (KeyboardInterrupt, Cancelled):
        return False
    return answer == yes


def command_weights(args):
    group_path = args.get("group")
    file_path = Path(args["config_path"]) / FILE_CONFIG
    shown_path = display_path(file_path)

    config = load_config(file_path, shown_path)
    groups = select_groups(config, group_path)

    print_rule("MSGram")
    if not group_path:
        print_header(groups)

    try:
        entries = run_groups(groups, single_group=bool(group_path))
    except (KeyboardInterrupt, Cancelled):
        console.line()
        print_output(
            _("Cancelled. {path} was not changed.").format(path=shown_path), "warning"
        )
        sys.exit(130)

    changed = [(g, a, r) for g, a, r in entries if a or g.weights != r.weights]
    if not changed:
        console.line()
        print_info(_("No weights to change."))
        return

    print_summary(changed, partial=bool(group_path))

    if not confirm_save(shown_path):
        print_output(
            _("Weights not saved. {path} was not changed.").format(path=shown_path),
            "warning",
        )
        return

    save_config(
        file_path, apply_weights(config, {g.path: r.weights for g, _, r in changed})
    )
    print_output(_("✔ Weights saved to {path}.").format(path=shown_path), "success")


def run_groups(groups, single_group: bool):
    """Pergunta cada grupo e devolve (grupo, respostas, resultado)."""
    entries = []
    to_ask = [g for g in groups if len(g.entities) > 1]
    position = 0
    for group in groups:
        if len(group.entities) <= 1:
            # Cenário 3: sem perguntas, peso 100
            entries.append((group, [], calculate_group(group.entities, [])))
            if single_group:
                print_output(
                    _("{label}: one entity, weight 100 with no questions").format(
                        label=group.label
                    ),
                    "muted",
                )
            continue
        position += 1
        title = (
            _("Group")
            if single_group
            else _("Group {position}/{total}").format(
                position=position, total=len(to_ask)
            )
        )
        answers, result = ask_group(group, title)
        entries.append((group, answers, result))
    return entries
