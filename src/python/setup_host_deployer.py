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

import os
import shutil
from typing import List

import click

from src.python.deployer import Deployer
from src.python.utils import (
    colorize_info,
    colorize_prompt,
    shell_command,
)


class SetupHostDeployer(Deployer):
    """
    Configures an existing remote host with Isaac Sim/Lab using Ansible only.
    Skips all Terraform infrastructure provisioning.
    """

    def __init__(self, params, config):
        super().__init__(params, config)

    def run_ansible(
        self,
        playbook_name: str,
        cwd: str,
        tags: List[str] = None,
        skip_tags: List[str] = None,
    ):
        """
        Override parent method to execute ansible directly without prompts.
        """
        if tags is None:
            tags = []
        if skip_tags is None:
            skip_tags = []

        # Call parent method to execute the playbook directly
        super().run_ansible(playbook_name, cwd, tags, skip_tags)

    def run_all_ansible(self):
        """
        Override parent method to run only Isaac playbook for setup-host.
        """
        # For setup-host, we only run Isaac playbook
        if "isaac" in self.params and self.params["isaac"]:
            click.echo(colorize_info("* Running Ansible for Isaac Sim..."))
            self.run_ansible(
                playbook_name="isaac",
                cwd=f"{self.config['ansible_dir']}",
            )

    def ask_existing_behavior(self):
        """
        Handle existing deployment behavior based on environment variable.
        Override parent method to avoid prompting unless explicitly requested.
        """
        deployment_name = self.params["deployment_name"]
        existing = self.params["existing"]

        self.existing_behavior = existing

        # Check if deployment exists
        deployment_exists = os.path.isfile(
            f"{self.config['state_dir']}/{deployment_name}/.inventory"
        )

        if deployment_exists:
            if existing == "ask":
                # Only prompt if explicitly requested via env var
                self.existing_behavior = click.prompt(
                    text=colorize_prompt(
                        "* Deployment exists, what would you like to do?"
                    ),
                    type=click.Choice(["repair", "modify", "replace", "run_ansible"]),
                    default="replace",
                )
            else:
                click.echo(
                    colorize_info(
                        f"* Deployment '{deployment_name}' exists. "
                        f"Action: {existing}"
                    )
                )

        if (
            self.existing_behavior == "repair"
            or self.existing_behavior == "run_ansible"
        ):
            # For setup-host, we don't have original terraform state to
            # restore from. So we'll just proceed with the current parameters
            click.echo(
                colorize_info(
                    f"* Processing existing deployment '{deployment_name}' "
                    f"with action: {self.existing_behavior}"
                )
            )

        if self.existing_behavior == "replace" and deployment_exists:
            inventory_file = f"{self.config['state_dir']}/{deployment_name}/.inventory"
            if os.path.exists(inventory_file):
                os.remove(inventory_file)
                click.echo(colorize_info("* Removed existing deployment configuration"))

        self.save_meta()

    def _output_deployment_info(self, print_text=True):
        """Override to provide SSH connection info for remote host"""
        ssh_command = (
            f"ssh -i state/{self.params['deployment_name']}/key.pem "
            f"-o StrictHostKeyChecking=no "
            f"{self.params['ssh_user']}@{self.params['host_ip']}"
        )

        extra_info = f"""
* Remote Host Setup Complete!

* SSH Connection:
  {ssh_command}

* Remote Desktop Access:
  - noVNC: http://{self.params['host_ip']}:6080/vnc.html
  - VNC: {self.params['host_ip']}:5900 (password: {self.params['vnc_password']})

Note: All Isaac Sim operations will use your '{self.params['ssh_user']}' user account.
"""

        self.output_deployment_info(extra_text=extra_info, print_text=print_text)

    def output_deployment_info(self, extra_text: str = "", print_text=True):
        """
        Override parent method to avoid terraform calls and use host_ip
        directly. Print connection info for the user.
        Save info to file (_state_dir_/_deployment_name_/info.txt)
        """
        isaac = "isaac" in self.params and self.params["isaac"]
        vnc_password = self.params["vnc_password"]
        deployment_name = self.params["deployment_name"]
        host_ip = self.params["host_ip"]

        # templates
        nomachine_instruction = f"""* To connect to __app__ via NoMachine:

0. Download NoMachine client at https://downloads.nomachine.com/, 
   install and launch it.
1. Click "Add" button.
2. Enter Host: "__ip__".
3. In "Configuration" > "Use key-based authentication with a key you provide",
   select file "state/{deployment_name}/key.pem".
4. Click "Connect" button.
5. Enter username when prompted.
"""

        nonvc_instruction = f"""* To connect to __app__ via noVNC:

1. Open http://__ip__:6080/vnc.html?host=__ip__&port=6080 in your browser.
2. Click "Connect" and use password \"{vnc_password}\""""

        # print connection info
        instructions_file = f"{self.config['state_dir']}/{deployment_name}/info.txt"
        instructions = ""

        if isaac:
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
            from src.python.utils import colorize_result

            click.echo(colorize_result("\n" + instructions))

        # create <dn>/ directory if it doesn't exist
        from pathlib import Path

        Path(instructions_file).parent.mkdir(parents=True, exist_ok=True)
        # write file
        Path(instructions_file).write_text(instructions)

        return instructions

    def ssh_connection_command(self, ip: str):
        """Override parent method to use correct ssh_user"""
        r = f"ssh -i state/{self.params['deployment_name']}/key.pem "
        r += f"-o StrictHostKeyChecking=no {self.params['ssh_user']}@{ip}"
        if self.params["ssh_port"] != 22:
            r += f" -p {self.params['ssh_port']}"
        return r

    def copy_ssh_key(self):
        """Copy the provided SSH key to the deployment state directory"""
        deployment_name = self.params["deployment_name"]
        state_key_path = f"{self.config['state_dir']}/{deployment_name}/key.pem"

        # Create state directory if it doesn't exist
        os.makedirs(f"{self.config['state_dir']}/{deployment_name}", exist_ok=True)

        # Copy SSH key
        shutil.copy2(self.params["ssh_key"], state_key_path)

        # Set correct permissions
        os.chmod(state_key_path, 0o600)

        if self.params["debug"]:
            click.echo(colorize_info(f"* SSH key copied to {state_key_path}"))

    def create_ansible_inventory_for_host(self):
        """Create Ansible inventory file for the remote host"""
        deployment_name = self.params["deployment_name"]
        inventory_file = f"{self.config['state_dir']}/{deployment_name}/.inventory"

        # Read the inventory template
        template_file = f"{self.config['ansible_dir']}/inventory.template"

        with open(template_file, "r") as f:
            template = f.read()

        # Set defaults for missing cloud-specific values
        inventory_vars = {
            "cloud": "remote-host",
            "in_china": "False",
            "ssh_port": self.params["ssh_port"],
            "ssh_user": self.params["ssh_user"],  # Use SSH connection user
            "ngc_api_key": self.params["ngc_api_key"],
            "isaac_image": self.params["isaac_image"],
            "vnc_password": self.params["vnc_password"],
            "omniverse_user": self.params["omniverse_user"],
            "deployment_name": deployment_name,
            "isaaclab": self.params["isaaclab"],
            "omniverse_password": self.params["omniverse_password"],
            "config": {
                **self.config,
                # Format the directory paths with actual user
                "default_remote_uploads_dir": self.config[
                    "default_remote_uploads_dir"
                ].format(user=self.params["ssh_user"]),
                "default_remote_results_dir": self.config[
                    "default_remote_results_dir"
                ].format(user=self.params["ssh_user"]),
                "default_remote_workspace_dir": self.config[
                    "default_remote_workspace_dir"
                ].format(user=self.params["ssh_user"]),
            },
            "oige": self.params["oige"],
            "isaaclab_private_git": self.params["isaaclab_private_git"],
            "system_user_password": self.params["system_user_password"],
            "isaac_ip": self.params["host_ip"],
        }

        # Replace template variables
        inventory_content = template.format(**inventory_vars)

        # Write inventory file
        with open(inventory_file, "w") as f:
            f.write(inventory_content)

        if self.params["debug"]:
            click.echo(colorize_info(f"* Ansible inventory created: {inventory_file}"))
            click.echo(
                colorize_info(
                    f"* Using user: '{self.params['ssh_user']}' " f"for all operations"
                )
            )

    def test_ssh_connection(self):
        """Test SSH connection to the remote host"""
        deployment_name = self.params["deployment_name"]
        key_file = f"{self.config['state_dir']}/{deployment_name}/key.pem"

        cmd = (
            f"ssh -i {key_file} -o StrictHostKeyChecking=no "
            f"-o ConnectTimeout=10 -o BatchMode=yes "
            f"{self.params['ssh_user']}@{self.params['host_ip']} "
            f"-p {self.params['ssh_port']} 'echo SSH connection successful'"
        )

        try:
            result = shell_command(
                cmd,
                capture_output=True,
                verbose=self.params["debug"],
                exit_on_error=False,
            )

            if result.returncode == 0:
                click.echo(colorize_info("* SSH connection test successful"))
                return True
            else:
                click.echo(colorize_info("* SSH connection test failed"))
                return False

        except Exception as e:
            click.echo(colorize_info(f"* SSH connection test failed: {e}"))
            return False

    def main(self):
        """Main setup process for remote host"""

        # Ask what to do if deployment already exists
        self.ask_existing_behavior()

        # Check if ngc api key is valid and has access to Isaac Sim
        if self.params["isaac"]:
            self.validate_ngc_api_key(self.params["isaac_image"])

        # Copy SSH key to state directory
        self.copy_ssh_key()

        # Test SSH connection
        if not self.test_ssh_connection():
            click.echo(
                colorize_info(
                    "Warning: SSH connection test failed. "
                    "Continuing anyway, but Ansible may fail."
                )
            )

        # Create Ansible inventory for the remote host
        self.create_ansible_inventory_for_host()

        # Save deployment info
        self._output_deployment_info(print_text=False)

        # Run Ansible to configure the host
        click.echo(colorize_info("* Configuring remote host with Ansible..."))
        self.run_all_ansible()

        # Upload user data if requested
        if self.params["upload"]:
            self.upload_user_data()

        # Print final connection info
        self._output_deployment_info()

        click.echo(colorize_info("\n* Remote host setup completed successfully!"))
        click.echo(
            colorize_info(
                f"* You can now connect to your Isaac Sim environment "
                f"at {self.params['host_ip']}"
            )
        )
