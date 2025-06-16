# SPDX-FileCopyrightText: 2025 Francesca Da Ros <francesca.daros@uniud.it>
#
# SPDX-License-Identifier: Apache-2.0

import sys
import click


from pydantic import ValidationError
from .. models import Instance, Solution
from .. models.instance_models import  Instance

@click.group()
def cli():
    """This is the validator group"""
    pass

@cli.group()
def validator():
    """Commands related to instance and solution validator"""
    pass

@validator.command()
@click.argument('filename', type=click.File())
def instance(filename):
    try:
        c = Instance.model_validate_json(filename.read())    
        click.secho(f"Validation OK, instance signature: {c.signature}", fg='green')
    except ValidationError as e:
        click.secho(f"{e}", fg='red')


@validator.command()
@click.argument('instance-filename', type=click.File())
@click.argument('solution-filename', type=click.File())
def solution(instance_filename, solution_filename):
    try:
        i = Instance.model_validate_json(instance_filename.read())
        s = Solution.model_validate_json(solution_filename.read())    
        click.secho(f"Solution uploaded. About to check validity", fg='green')
        try:
            s.check_validity(i)
        except Exception as e:
            click.secho(f"{e}", fg="red")
            click.secho(f"Stopping validation. Exiting validator...", fg="red")
            sys.exit(1)
        click.secho(f"Validity checked. About to compute costs.", fg='green')
        s.compute_costs(i)
    except ValidationError as e:
        click.secho(f"{e}", fg='red')