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

from typing import Any, Dict

c: Dict[str, Any] = {}

# paths
c["app_dir"] = "/app"
c["state_dir"] = "/app/state"
c["results_dir"] = "/app/results"
c["uploads_dir"] = "/app/uploads"
c["tests_dir"] = "/app/src/tests"
c["ansible_dir"] = "/app/src/ansible"

# app image name
c["app_image_name"] = "isa"

# nvidia driver for generic installations
c["generic_driver_apt_package"] = "nvidia-driver-535-server"

# default remote dirs - will be formatted with actual username
c["default_remote_uploads_dir"] = "/home/{user}/uploads"
c["default_remote_results_dir"] = "/home/{user}/results"
c["default_remote_workspace_dir"] = "/home/{user}/workspace"

# defaults

# --isaac-image
c["default_isaac_image"] = "nvcr.io/nvidia/isaac-sim:4.5.0"

# --ssh-port
c["default_ssh_port"] = 22

# --omniverse-user
c["default_omniverse_user"] = "omniverse"

# --oige
c["default_oige_git_checkpoint"] = "no"

# --isaaclab
c["default_isaaclab_git_checkpoint"] = "v2.1.0"
# fixes https://github.com/isaac-sim/IsaacLab/issues/1807
