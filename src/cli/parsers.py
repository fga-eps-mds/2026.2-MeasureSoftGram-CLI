import argparse

from pathlib import Path

from src.cli.i18n import _
from src.cli.utils import THEME_CHOICES, print_help
from src.cli.commands.cmd_diff import command_diff
from src.cli.commands.cmd_init import command_init
from src.cli.commands.cmd_extract import command_extract
from src.cli.commands.cmd_calculate import command_calculate
from src.cli.commands.cmd_demo import command_demo
from src.cli.commands.cmd_list import command_list
from src.cli.commands.cmd_norm_diff import command_norm_diff
from src.cli.commands.cmd_weights import command_weights

from src.config.settings import (
    DEFAULT_CONFIG_PATH,
    AVAILABLE_GEN_FORMATS,
)


def config_path_help() -> str:
    return _("Path to the directory with the model configuration file (msgram.json).")


class ThemedArgumentParser(argparse.ArgumentParser):
    def print_help(self, file=None):
        help_text = self.format_help()
        if file is not None:
            file.write(help_text)
            return

        print_help(help_text)

    def print_usage(self, file=None):
        usage_text = self.format_usage()
        if file is not None:
            file.write(usage_text)
            return

        print_help(usage_text)

    def error(self, message):
        from src.cli.utils import print_error

        self.print_usage()
        print_error(
            _("{prog}: error: {message}").format(prog=self.prog, message=message)
        )
        self.exit(2)


def add_theme_argument(parser, default=argparse.SUPPRESS, dest="theme"):
    parser.add_argument(
        "--theme",
        dest=dest,
        choices=THEME_CHOICES,
        default=default,
        help=_("Terminal contrast theme. Use auto, dark, or light."),
    )


def create_parser():
    parser = ThemedArgumentParser(
        prog="msgram",
        description=_("Command line interface for measuresoftgram"),
        epilog=_("Thanks for using %(prog)s!"),
    )
    add_theme_argument(parser, default="auto")

    subparsers = parser.add_subparsers(
        title=_("subcommands"),
        dest="command",
        help=_("sub-command help"),
        parser_class=ThemedArgumentParser,
    )

    # =====================================< COMMAND init >=====================================
    parser_init = subparsers.add_parser(
        "init",
        help=_(
            "Create a init file `.measuresoftgram` with your default organization, product and repositories"
        ),
    )
    add_theme_argument(parser_init, dest="command_theme")

    parser_init.add_argument(
        "-cp",
        "--config_path",
        type=lambda p: Path(p).absolute(),
        default=DEFAULT_CONFIG_PATH,
        help=config_path_help(),
    )
    parser_init.set_defaults(func=command_init)  # function command init

    # =====================================< COMMAND demo >=====================================
    parser_demo = subparsers.add_parser(
        "demo",
        help=_(
            "Run an end-to-end pipeline (init, extract, calculate) on an embedded sample dataset."
        ),
    )
    add_theme_argument(parser_demo, dest="command_theme")

    parser_demo.add_argument(
        "-o",
        "--output_path",
        type=lambda p: Path(p).absolute(),
        default=Path.cwd() / "msgram-demo",
        help=_("Path to the working directory where the demo results are written."),
    )

    parser_demo.add_argument(
        "-of",
        "--output_format",
        type=str,
        choices=AVAILABLE_GEN_FORMATS,
        default="csv",
        help=_(
            "The format of the calculate output (export) values are: {formats}"
        ).format(formats=", ".join(AVAILABLE_GEN_FORMATS)),
    )
    parser_demo.set_defaults(func=command_demo)  # function command demo

    # =====================================< COMMAND list >=====================================
    parser_list_config = subparsers.add_parser(
        "list",
        help=_("Listing configurations parameters."),
    )
    add_theme_argument(parser_list_config, dest="command_theme")

    parser_list_config.add_argument(
        "-cp",
        "--config_path",
        type=lambda p: Path(p).absolute(),
        default=DEFAULT_CONFIG_PATH,
        help=config_path_help(),
    )

    parser_list_config.add_argument(
        "all",
        nargs="?",
        help=_("Show configuration file."),
    )

    parser_list_config.set_defaults(func=command_list)  # function command list config

    # =====================================< COMMAND weights >=====================================
    parser_weights = subparsers.add_parser(
        "weights",
        help=_("Define the model weights by pairwise comparison (AHP)."),
    )
    add_theme_argument(parser_weights, dest="command_theme")

    parser_weights.add_argument(
        "-cp",
        "--config_path",
        type=lambda p: Path(p).absolute(),
        default=DEFAULT_CONFIG_PATH,
        help=_(
            "Path to the directory with the model configuration file (msgram.json)."
        ),
    )

    parser_weights.add_argument(
        "--group",
        type=str,
        default=None,
        help=_(
            "Redefine only one group, e.g. characteristics or reliability/subcharacteristics."
        ),
    )
    parser_weights.set_defaults(func=command_weights)  # function command weights

    # =====================================< COMMAND extract >=====================================
    parser_extract = subparsers.add_parser(
        "extract", help=_("Extract supported metrics")
    )
    add_theme_argument(parser_extract, dest="command_theme")

    parser_extract.add_argument(
        "-sp",
        "--sonar_path",
        type=lambda p: Path(p).absolute(),
        help=_("Path to analysis data directory"),
    )

    parser_extract.add_argument(
        "-ep",
        "--extracted_path",
        type=lambda p: Path(p).absolute(),
        default=DEFAULT_CONFIG_PATH,
        help=_("Path to the extracted directory"),
    )

    parser_extract.add_argument(
        "-gl",
        "--gh_label",
        type=str,
        help=_(
            "Selected label name to be considered in the Story Issues extraction."
            ' Format "XX YY", including quotation marks.'
            ' Default, not case sensitive: "US", "User Story" or "User Stories".'
        ),
    )

    parser_extract.add_argument(
        "-gw",
        "--gh_workflows",
        type=str,
        help=_(
            "Selected workflow name to be considered in the CI Feedback Time extraction."
            ' Format "XX YY", including quotation marks.'
            ' Default, not case sensitive: "build".'
        ),
    )

    parser_extract.add_argument(
        "-gd",
        "--gh_date_range",
        type=str,
        help=_(
            'Filter range of dates considered on extraction, with format "dd/mm/yyyy-dd/mm/yyyy"'
            ", including quotation marks."
        ),
    )

    parser_extract.add_argument(
        "-gr",
        "--gh_repository",
        type=str,
        help=_("Path to analysis git repository"),
    )

    parser_extract.add_argument(
        "-p1",
        "--pe_release_1",
        type=lambda p: Path(p).absolute(),
        help=_(
            "Path to the .csv file of the first release, used for extracting performance efficiency data"
        ),
    )

    parser_extract.add_argument(
        "-p2",
        "--pe_release_2",
        type=lambda p: Path(p).absolute(),
        help=_(
            "Path to the .csv file of the second release, used for extracting performance efficiency data"
        ),
    )

    parser_extract.add_argument(
        "-pn",
        "--pe_repository_name",
        type=str,
        help=_(
            "Name of the repository associated with the extracted performance efficiency data"
        ),
    )

    parser_extract.set_defaults(func=command_extract)  # function command extract

    # =====================================< COMMAND calculate >=====================================
    parser_calculate = subparsers.add_parser(
        "calculate",
        help=_("Calculates all entities"),
    )
    add_theme_argument(parser_calculate, dest="command_theme")

    parser_calculate.add_argument(
        "-ep",
        "--extracted_path",
        type=lambda p: Path(p).absolute(),
        default=DEFAULT_CONFIG_PATH,
        help=_("Path to the extracted directory"),
    )

    parser_calculate.add_argument(
        "-cp",
        "--config_path",
        type=lambda p: Path(p).absolute(),
        default=DEFAULT_CONFIG_PATH,
        help=config_path_help(),
    )

    parser_calculate.add_argument(
        "-o",
        "--output_format",
        type=str,
        choices=AVAILABLE_GEN_FORMATS,
        default="csv",
        help=_("The format of the output (export) values are: {formats}").format(
            formats=", ".join(AVAILABLE_GEN_FORMATS)
        ),
    )
    parser_calculate.set_defaults(func=command_calculate)  # function command calculate

    # =====================================< COMMAND norm_diff >=====================================
    parser_norm_diff = subparsers.add_parser(
        "norm_diff",
        help=_(
            "Calculates the Frobenius norm of the difference between tensors RP and RD, which means the quantitative "
            "perception of the discrepancy between the planned and developed quality requirements in a release."
        ),
    )
    add_theme_argument(parser_norm_diff, dest="command_theme")

    parser_norm_diff.add_argument(
        "-rp",
        "--rp_path",
        type=lambda p: Path(p).absolute(),
        required=True,
        help=_(
            "path to the .json file with the planned/wished values for the quality "
            "characteristics of a release. quality requirements goals for a release."
        ),
    )

    parser_norm_diff.add_argument(
        "-rd",
        "--rd_path",
        type=lambda p: Path(p).absolute(),
        required=True,
        help=_(
            "path to the .json file with the model-calculated values for a release's "
            "quality characteristics observed/developed."
        ),
    )

    parser_norm_diff.set_defaults(
        func=command_norm_diff
    )  # function command list config

    # =====================================< COMMAND diff >=====================================
    parser_calculate = subparsers.add_parser(
        "diff",
        help=_(
            "Calculates and interprets the difference between the planned and developed quantitative perceptions "
            "of each quality characteristic, represented by the RP and RD tensors."
        ),
    )
    add_theme_argument(parser_calculate, dest="command_theme")

    parser_calculate.add_argument(
        "-rd",
        "--rd_path",
        type=lambda p: Path(p).absolute(),
        required=True,
        help=_(
            "Path to the .json file with the model-calculated values for a release's quality "
            "characteristics observed/developed."
        ),
    )

    parser_calculate.add_argument(
        "-rp",
        "--rp_path",
        type=lambda p: Path(p).absolute(),
        required=True,
        help=_(
            "Path to the .json file with the planned/wished values for the quality characteristics "
            "of a release. Quality requirements goals for a release."
        ),
    )

    parser_calculate.add_argument(
        "-of",
        "--output_format",
        type=str,
        choices=AVAILABLE_GEN_FORMATS,
        help=_("The format of the output (export) values is tabular"),
    )
    parser_calculate.set_defaults(func=command_diff)

    return parser
