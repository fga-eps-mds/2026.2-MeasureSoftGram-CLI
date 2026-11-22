import json
import logging
import sys
from pathlib import Path

from staticfiles import DEFAULT_PRE_CONFIG

from src.cli.i18n import _
from src.cli.utils import (
    ask_confirm,
    clear_console,
    console,
    print_error,
    print_panel,
    print_rule,
    print_success,
    print_warn,
)
from src.config.settings import FILE_CONFIG

logger = logging.getLogger("msgram")


def command_init(args):
    try:
        config_path: Path = args["config_path"]

    except Exception as e:
        logger.error(f"KeyError: args[{e}] - non-existent parameters")
        print_error(
            _("KeyError: args[{error}] - non-existent parameters").format(error=e)
        )
        sys.exit(1)

    logger.debug(config_path)
    file_path = config_path / FILE_CONFIG

    clear_console()
    print_rule("MSGram", _("Init to set config file:"))

    if not config_path.exists():
        print_success(_("Created dir: {path}").format(path=config_path))
        config_path.mkdir()

    replace = True

    if file_path.exists():
        print_warn(
            _("MSGram config file '{file}' exists already!").format(file=FILE_CONFIG)
        )
        replace = ask_confirm(
            _("> Do you want to replace '{file}'?").format(file=FILE_CONFIG)
        )

    if replace:
        try:
            with file_path.open("w") as f:
                f.write(json.dumps(DEFAULT_PRE_CONFIG, indent=4))
        except OSError:
            console.line(2)
            print_error(_("Error opening or writing to file"))
        print_success(
            _("The file config: '{dir}/msgram.json' was created successfully.").format(
                dir=config_path.name
            )
        )

    else:
        print_warn(
            _("The file config: '{dir}/msgram.json' not changed...").format(
                dir=config_path.name
            )
        )

    print_panel(
        _(
            "> Run msgram extract -o <source of information> -dp data_path -ep extract_path,\n"
            "  to extract supported metrics!"
        )
    )
