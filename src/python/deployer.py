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

import json
import os
import re
import shlex
import sys
from pathlib import Path

import click

from src.python.debug import debug_break  # noqa
from src.python.ngc import check_ngc_access
from src.python.utils import (
    colorize_error,
    colorize_info,
    colorize_prompt,
    colorize_result,
    read_meta,
    shell_command,
)


class Deployer:
    def __init__(self, params, config):
        self.tf_outputs = {}
        self.params = params
        self.config = config
        self.existing_behavior = None

        # save original params so we can recreate command line
        self.input_params = params.copy()

        # convert "in_china"
        self.params["in_china"] = {"yes": True, "no": False, "auto": False}[
            self.params["in_china"]
        ]

        # create state directory if it doesn't exist
        os.makedirs(self.config["state_dir"], exist_ok=True)

        # print complete command line
        if self.params["debug"]:
            click.echo(colorize_info("* Command:\n" + self.recreate_command_line()))

    def __del__(self):
        # update meta info
        self.save_meta()

    def save_meta(self):
        """
        Save command parameters in json file, just in case
        """

        meta_file = (
            f"{self.config['state_dir']}/{self.params['deployment_name']}/meta.json"
        )

        data = {
            "command": self.recreate_command_line(separator=" "),
            "input_params": self.input_params,
            "params": self.params,
            "config": self.config,
        }

        Path(meta_file).parent.mkdir(parents=True, exist_ok=True)
        Path(meta_file).write_text(json.dumps(data, indent=4))

        if self.params["debug"]:
            click.echo(colorize_info(f"* Meta info saved to '{meta_file}'"))

    def read_meta(self):
        return read_meta(
            self.params["deployment_name"],
            self.params["debug"],
        )

    def recreate_command_line(self, separator=" \\\n"):
        """
        Recreate command line
        """

        command_line = sys.argv[0]

        for k, v in self.input_params.items():
            k = k.replace("_", "-")

            if isinstance(v, bool):
                if v:
                    command_line += separator + "--" + k
                else:
                    not_prefix = "--no-"

                    if k in ["from-image"]:
                        not_prefix = "--not-"

                    command_line += separator + not_prefix + k
            else:
                command_line += separator + "--" + k + " "

                if isinstance(v, str):
                    command_line += "'" + shlex.quote(v) + "'"
                else:
                    command_line += str(v)

        return command_line

    def ask_existing_behavior(self):
        """
        Ask what to do if deployment already exists
        """

        deployment_name = self.params["deployment_name"]
        existing = self.params["existing"]

        self.existing_behavior = existing

        if existing == "ask" and os.path.isfile(
            f"{self.config['state_dir']}/{deployment_name}/.inventory"
        ):
            self.existing_behavior = click.prompt(
                text=colorize_prompt(
                    "* Deployment exists, what would you like to do? See --help for details."
                ),
                type=click.Choice(["repair", "modify", "replace", "run_ansible"]),
                default="replace",
            )

        if (
            self.existing_behavior == "repair"
            or self.existing_behavior == "run_ansible"
        ):
            # restore params from meta file
            r = self.read_meta()
            self.params = r["params"]

            click.echo(
                colorize_info(
                    f"* Repairing existing deployment \"{self.params['deployment_name']}\"..."
                )
            )

        # update meta info (with new value for existing_behavior)
        self.save_meta()

        # destroy existing deployment
        if self.existing_behavior == "replace":
            debug = self.params["debug"]
            click.echo(colorize_info("* Deleting existing deployment..."))

            # For SSH setup, just remove the inventory file
            inventory_file = f"{self.config['state_dir']}/{deployment_name}/.inventory"
            if os.path.exists(inventory_file):
                os.remove(inventory_file)
                if debug:
                    click.echo(colorize_info(f"* Removed {inventory_file}"))

            # update meta info if deployment was destroyed
            self.save_meta()

    def validate_ngc_api_key(self, image, restricted_image=False):
        """
        Check if NGC API key allows to log in and has access to appropriate NGC image
        @param image: NGC image to check access to
        @param restricted_image: If image is restricted to specific org/team?
        """

        debug = self.params["debug"]
        ngc_api_key = self.params["ngc_api_key"]
        ngc_api_key_check = self.params["ngc_api_key_check"]

        # extract org and team from the image path

        r = re.findall(
            "^nvcr\\.io/([a-z0-9\\-_]+)/([a-z0-9\\-_]+/)?[a-z0-9\\-_]+:[a-z0-9\\-_.]+$",
            image,
        )

        ngc_org, ngc_team = r[0]
        ngc_team = ngc_team.rstrip("/")

        if ngc_org == "nvidia":
            click.echo(
                colorize_info(
                    "* Access to docker image can't be checked for NVIDIA org. But you'll be fine. Fingers crossed."
                )
            )
            return

        if debug:
            click.echo(colorize_info(f'* Will check access to NGC Org: "{ngc_org}"'))
            click.echo(colorize_info(f'* Will check access to NGC Team: "{ngc_team}"'))

        if ngc_api_key_check and ngc_api_key != "none":
            click.echo(colorize_info("* Validating NGC API key... "))
            r = check_ngc_access(
                ngc_api_key=ngc_api_key, org=ngc_org, team=ngc_team, verbose=debug
            )
            if r == 100:
                raise Exception(colorize_error("NGC API key is invalid."))
            # only check access to org/team if restricted image is deployed
            elif restricted_image and (r == 101 or r == 102):
                raise Exception(
                    colorize_error(
                        f'NGC API key is valid but you don\'t have access to image "{image}".'
                    )
                )
            click.echo(colorize_info(("* NGC API Key is valid!")))

    def create_ansible_inventory(self, write: bool = True):
        """
        Create Ansible inventory, return it as text
        Write to file if write=True
        """

        debug = self.params["debug"]
        deployment_name = self.params["deployment_name"]

        ansible_vars = self.params.copy()

        # add config
        ansible_vars["config"] = self.config

        # convert booleans to ansible format
        ansible_booleans = {True: "true", False: "false"}
        for k, v in ansible_vars.items():
            if isinstance(v, bool):
                ansible_vars[k] = ansible_booleans[v]

        template = Path(f"{self.config['ansible_dir']}/inventory.template").read_text()
        res = template.format(**ansible_vars)

        # write to file
        if write:
            inventory_file = f"{self.config['state_dir']}/{deployment_name}/.inventory"
            Path(inventory_file).parent.mkdir(parents=True, exist_ok=True)  # create dir
            Path(inventory_file).write_text(res)  # write file
            if debug:
                click.echo(
                    colorize_info(
                        f'* Created Ansible inventory file "{inventory_file}"'
                    )
                )

        return res

    def run_ansible(
        self,
        playbook_name: str,
        cwd: str,
        tags: [str] = [],
        skip_tags: [str] = [],
    ):
        """
        Run Ansible playbook via shell command
        """

        debug = self.params["debug"]
        deployment_name = self.params["deployment_name"]

        if len(tags) > 0:
            tags = ",".join([f'--tags "{tag}"' for tag in tags])
        else:
            tags = ""

        if len(skip_tags) > 0:
            skip_tags = ",".join([f'--skip-tags "{tag}"' for tag in skip_tags])
        else:
            skip_tags = ""

        shell_command(
            f"ansible-playbook -i {self.config['state_dir']}/{deployment_name}/.inventory "
            + f"{playbook_name}.yml {tags} {skip_tags} {'-vv' if self.params['debug'] else ''}",
            cwd=cwd,
            verbose=debug,
        )

    def run_all_ansible(self):
        # run ansible for isaac
        if "isaac" in self.params and self.params["isaac"]:

            click.echo(colorize_info("* Running Ansible for Isaac Sim..."))
            self.run_ansible(
                playbook_name="isaac",
                cwd=f"{self.config['ansible_dir']}",
            )

    def upload_user_data(self):
        shell_command(
            f'./upload "{self.params["deployment_name"]}" '
            + f'{"--debug" if self.params["debug"] else ""}',
            cwd=self.config["app_dir"],
            verbose=self.params["debug"],
            exit_on_error=True,
            capture_output=False,
        )

    # generate ssh connection command for the user
    def ssh_connection_command(self, ip: str):
        r = f"ssh -i state/{self.params['deployment_name']}/key.pem "
        r += f"-o StrictHostKeyChecking=no {self.params['ssh_user']}@{ip}"
        if self.params["ssh_port"] != 22:
            r += f" -p {self.params['ssh_port']}"
        return r

    def output_deployment_info(self, extra_text: str = "", print_text=True):
        """
        Print connection info for the user
        Save info to file (_state_dir_/_deployment_name_/info.txt)
        """

        isaac = "isaac" in self.params and self.params["isaac"]

        vnc_password = self.params["vnc_password"]
        deployment_name = self.params["deployment_name"]

        # templates
        nomachine_instruction = f"""* To connect to __app__ via NoMachine:

0. Download NoMachine client at https://downloads.nomachine.com/, install and launch it.
1. Click "Add" button.
2. Enter Host: "__ip__".
3. In "Configuration" > "Use key-based authentication with a key you provide",
   select file "state/{deployment_name}/key.pem".
4. Click "Connect" button.
5. Enter "{self.params['ssh_user']}" as a username when prompted.
"""

        vnc_instruction = f"""* To connect to __app__ via VNC:

- IP: __ip__
- Port: 5900
- Password: {vnc_password}"""

        nonvc_instruction = f"""* To connect to __app__ via noVNC:

1. Open http://__ip__:6080/vnc.html?host=__ip__&port=6080 in your browser.
2. Click "Connect" and use password \"{vnc_password}\""""

        # print connection info

        instructions_file = f"{self.config['state_dir']}/{deployment_name}/info.txt"
        instructions = ""

        if isaac:
            # For SSH setup, we need to use the host_ip directly instead of tf_output
            host_ip = self.params.get("host_ip", "")
            instructions += f"""{'*' * (29+len(host_ip))}
* Isaac Sim is deployed at {host_ip} *
{'*' * (29+len(host_ip))}

* To connect to Isaac Sim via SSH:

{self.ssh_connection_command(host_ip)}

{nonvc_instruction}

{nomachine_instruction}""".replace(
                "__app__", "Isaac Sim"
            ).replace(
                "__ip__", host_ip
            )

        # extra text
        if len(extra_text) > 0:
            instructions += extra_text + "\n"

        # print instructions for the user
        if print_text:
            click.echo(colorize_result("\n" + instructions))

        # create <dn>/ directory if it doesn't exist
        Path(instructions_file).parent.mkdir(parents=True, exist_ok=True)
        # write file
        Path(instructions_file).write_text(instructions)

        return instructions
