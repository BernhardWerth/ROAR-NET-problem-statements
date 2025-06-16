# SPDX-FileCopyrightText: 2025 Francesca Da Ros <francesca.daros@uniud.it>
#
# SPDX-License-Identifier: Apache-2.0

import click
import warnings
# warnings.simplefilter("always")

commands = []

from .. validator.cli import cli as cli_validator
commands.append(cli_validator)
 
def main_cli():
    cli = click.CommandCollection(sources=commands)
    cli(obj={})
