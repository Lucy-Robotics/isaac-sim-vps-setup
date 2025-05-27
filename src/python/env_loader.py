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
from pathlib import Path

import randomname
import pwgen


def load_dotenv():
    """Load environment variables from .env file if it exists

    Only sets environment variables if they are not already set,
    so existing environment variables take precedence over .env file values.
    """
    env_file = Path(".env")
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()
                    # Remove quotes if present
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    # Only set if not already set in environment
                    if key not in os.environ:
                        os.environ[key] = value


def get_env_bool(key: str, default: bool = False) -> bool:
    """Get boolean environment variable"""
    value = os.environ.get(key, str(default)).lower()
    return value in ("true", "yes", "1", "on")


def get_env_str(key: str, default: str = "") -> str:
    """Get string environment variable"""
    return os.environ.get(key, default)


def get_env_int(key: str, default: int) -> int:
    """Get integer environment variable"""
    try:
        return int(os.environ.get(key, str(default)))
    except ValueError:
        return default


def get_setup_host_params():
    """Get all setup-host parameters from environment variables"""

    # Load .env file if it exists
    load_dotenv()

    # Required variables with validation
    host_ip = get_env_str("HOST_IP")
    if not host_ip:
        raise ValueError("HOST_IP environment variable is required")

    ssh_key_path = get_env_str("SSH_KEY_PATH")
    if not ssh_key_path:
        raise ValueError("SSH_KEY_PATH environment variable is required")

    # Expand user path
    ssh_key_path = os.path.expanduser(ssh_key_path)
    if not os.path.exists(ssh_key_path):
        raise ValueError(f"SSH key file not found: {ssh_key_path}")

    ngc_api_key = get_env_str("NGC_API_KEY")
    if not ngc_api_key:
        raise ValueError("NGC_API_KEY environment variable is required")

    # Optional variables with defaults
    deployment_name = get_env_str("DEPLOYMENT_NAME")
    if not deployment_name:
        deployment_name = randomname.get_name()

    # Generate passwords if not provided
    vnc_password = get_env_str("VNC_PASSWORD")
    if not vnc_password:
        vnc_password = pwgen.pwgen(10)

    system_user_password = get_env_str("SYSTEM_USER_PASSWORD")
    if not system_user_password:
        system_user_password = pwgen.pwgen(10)

    omniverse_password = get_env_str("OMNIVERSE_PASSWORD")
    if not omniverse_password:
        omniverse_password = pwgen.pwgen(10)

    return {
        # Required parameters
        "host_ip": host_ip,
        "ssh_key": ssh_key_path,
        "ngc_api_key": ngc_api_key,
        # SSH configuration
        "ssh_user": get_env_str("SSH_USER", "ubuntu"),
        "ssh_port": get_env_int("SSH_PORT", 22),
        # Deployment configuration
        "deployment_name": deployment_name,
        "existing": get_env_str("EXISTING_DEPLOYMENT_ACTION", "replace"),
        # Legacy cloud parameter (not used for setup-host)
        "in_china": "no",
        # Isaac Sim configuration
        "isaac": get_env_bool("ISAAC_ENABLED", True),
        "isaac_image": get_env_str("ISAAC_IMAGE", "nvcr.io/nvidia/isaac-sim:4.5.0"),
        # Isaac Lab configuration
        "isaaclab": get_env_str("ISAACLAB_VERSION", "v2.1.0"),
        "isaaclab_private_git": get_env_str("ISAACLAB_PRIVATE_GIT", ""),
        # Omniverse Isaac Gym Envs (deprecated)
        "oige": get_env_str("OIGE_VERSION", "no"),
        # Passwords
        "vnc_password": vnc_password,
        "system_user_password": system_user_password,
        "omniverse_password": omniverse_password,
        # Omniverse configuration
        "omniverse_user": get_env_str("OMNIVERSE_USER", "omniverse"),
        # File management
        "upload": get_env_bool("UPLOAD_FILES", True),
        # Development/debug
        "debug": get_env_bool("DEBUG", False),
        "ngc_api_key_check": get_env_bool("NGC_API_KEY_CHECK", True),
    }


def validate_required_env_vars():
    """Validate that all required environment variables are set"""
    required_vars = ["HOST_IP", "SSH_KEY_PATH", "NGC_API_KEY"]
    missing_vars = []

    load_dotenv()

    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)

    if missing_vars:
        env_file_msg = ""
        if not Path(".env").exists():
            env_file_msg = (
                "\n\nCreate a .env file from .env.example and fill in your "
                "values:\n  cp .env.example .env"
            )

        raise ValueError(
            f"Missing required environment variables: "
            f"{', '.join(missing_vars)}"
            f"{env_file_msg}"
        )
