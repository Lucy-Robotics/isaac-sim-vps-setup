# region copyright
# Copyright 2023 NVIDIA Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# endregion


"""
CLI Utils
"""

import json
import os
import subprocess
from glob import glob
from pathlib import Path

import click

from src.python.config import c as config


def colorize_prompt(text):
    return click.style(text, fg="bright_cyan", italic=True)


def colorize_error(text):
    return click.style(text, fg="bright_red", italic=True)


def colorize_info(text):
    return click.style(text, fg="bright_magenta", italic=True)


def colorize_result(text):
    return click.style(text, fg="bright_green", italic=True)


def shell_command(
    command, verbose=False, cwd=None, exit_on_error=True, capture_output=False
):
    """
    Execute shell command, print it if debug is enabled
    """

    if verbose:
        if cwd is not None:
            click.echo(colorize_info(f"* Running `(cd {cwd} && {command})`..."))
        else:
            click.echo(colorize_info(f"* Running `{command}`..."))

    res = subprocess.run(
        command,
        shell=True,
        cwd=cwd,
        capture_output=capture_output,
    )

    if res.returncode == 0:
        if verbose and res.stdout is not None:
            click.echo(res.stdout.decode())

    elif exit_on_error:
        if res.stderr is not None:
            click.echo(
                colorize_error(f"Error: {res.stderr.decode()}"),
                err=True,
            )
        exit(1)

    return res


def deployments():
    """List existing deployments by name"""
    state_dir = config["state_dir"]
    deployments = sorted(
        [
            os.path.basename(os.path.dirname(d))
            for d in glob(os.path.join(state_dir, "*/"))
        ]
    )
    return deployments


def read_meta(deployment_name: str, verbose: bool = False):
    """
    Read metadata from json file
    """

    meta_file = f"{config['state_dir']}/{deployment_name}/meta.json"

    if os.path.isfile(meta_file):
        data = json.loads(Path(meta_file).read_text())
        if verbose:
            click.echo(colorize_info(f"* Meta info loaded from '{meta_file}'"))
        return data

    raise Exception(f"Meta file '{meta_file}' not found")


def format_app_name(app_name):
    """
    Format app name for user output
    """

    formatted = {
        "isaac": "Isaac Sim",
    }

    if app_name in formatted:
        return formatted[app_name]

    return app_name
