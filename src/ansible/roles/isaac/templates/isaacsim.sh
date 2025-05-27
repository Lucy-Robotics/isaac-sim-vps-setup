#!/bin/bash

# default parameter values

# isaac sim startup command
CMD="/isaac-sim/kit/kit \
      /isaac-sim/apps/isaacsim.exp.full.kit \
      --ext-folder /isaac-sim/apps \
      --allow-root"

DISPLAY=":0"
CONTAINER_NAME="isaacsim"
OUT_DIR="{{ results_dir }}"
UPLOADS_DIR="{{ uploads_dir }}"
WORKSPACE_DIR="{{ workspace_dir }}"
OMNI_USER="{{ omniverse_user }}"
OMNI_PASS="{{ omniverse_password }}"
DOCKER_IMAGE="{{ isaac_image }}"
CACHE_DIR="{{ isaac_cache_dir }}"
NUCLEUS_SERVER_NAME="{{ nucleus_uri }}"

# detect vulkan location
if [ -f /usr/share/vulkan/icd.d/nvidia_icd.json ]
then
  VULKAN_DIR="/usr/share/vulkan"
elif [ -f /etc/vulkan/icd.d/nvidia_icd.json ]
then
  VULKAN_DIR="/etc/vulkan"
else
  echo "ERROR: Could not detect Vulkan installation directory"
  exit 1
fi

# find .Xauthority
XAUTHORITY_LOCATION=$(systemctl --user show-environment | grep XAUTHORITY | cut -c 12-)

# process named arguments
while [ $# -gt 0 ]; do
  case "$1" in
      
    --help|-h)
      echo "Usage: `basename $0` \\"
      echo "  [--command=..] \\"
      echo "  [--out_dir=..] \\"
      echo "  [--omni_user=..] \\"
      echo "  [--omni_pass=..] \\"
      echo "  [--docker_image=..] \\"
      echo "  [--container_name=..] \\"
      echo "  [--nucleus_server=..]"
      echo
      echo "Defaults: "
      echo "  --command='${CMD}'"
      echo "  --out_dir='${OUT_DIR}'"
      echo "  --omni_user='${OMNI_USER}'"
      echo "  --omni_pass='${OMNI_PASS}'"
      echo "  --docker_image='${DOCKER_IMAGE}'"
      echo "  --container_name='${CONTAINER_NAME}'"
      echo "  --nucleus_server='${NUCLEUS_SERVER_NAME}'"
      exit
      ;;

    --debug)
      set -x
      ;;

    --nucleus=*|--nucleus_server=*|--nucleus_server_name=*|--nucleus_url=*|--nucleus_ip=*)
      NUCLEUS_SERVER_NAME="${1#*=}"
      ;;

    --user=*|--username=*|--omni_user=*)
      OMNI_USER="${1#*=}"
      ;;
      
    --pass=*|--password=*|--omni_pass=*)
      OMNI_PASS="${1#*=}"
      ;;

    --image=*|--docker_image=*)
      DOCKER_IMAGE="${1#*=}"
      ;;

    --out=*|--output=*|--out_dir=*|--output_dir=*)
      OUT_DIR="${1#*=}"
      ;;

    --uploads_dir=*)
      UPLOADS_DIR="${1#*=}"
      ;;

    --workspace_dir=*)
      WORKSPACE_DIR="${1#*=}"
      ;;

    --display=*)
      DISPLAY="${1#*=}"
      ;;

    --cmd=*|--command=*)
      CMD="${1#*=}"
      ;;

    --container-name=*|--name=*)
      CONTAINER_NAME="${1#*=}"
      ;;

  esac
  shift
done

# create cache dir if it doesn't exist, assign permissions
[ ! -d "${CACHE_DIR}" ] && mkdir -pv "${CACHE_DIR}"
[ -d "${CACHE_DIR}" ] && chmod 0777 "${CACHE_DIR}"
mkdir -pv "${CACHE_DIR}/ov" "${CACHE_DIR}/pip" "${CACHE_DIR}/glcache" "${CACHE_DIR}/computecache" "${CACHE_DIR}/logs" "${CACHE_DIR}/config" "${CACHE_DIR}/data" "${CACHE_DIR}/documents" 2>/dev/null

# create output/uploads/workspace dirs if it doesn't exist
for d in "${OUT_DIR}" "${UPLOADS_DIR}" "${WORKSPACE_DIR}"; do
  [ ! -d "${d}" ] && mkdir -pv "${d}"
done

# kill any existing container
docker kill $CONTAINER_NAME 2>/dev/null

docker run --name isaac-sim --entrypoint bash -it --rm \
    --runtime=nvidia \
    --gpus all \
    -e "ACCEPT_EULA=Y" \
    -e "PRIVACY_CONSENT=Y" \
    -v ~/docker/isaac-sim/cache/kit:/isaac-sim/kit/cache:rw \
    -v ~/docker/isaac-sim/cache/ov:/root/.cache/ov:rw \
    -v ~/docker/isaac-sim/cache/pip:/root/.cache/pip:rw \
    -v ~/docker/isaac-sim/cache/glcache:/root/.cache/nvidia/GLCache:rw \
    -v ~/docker/isaac-sim/cache/computecache:/root/.nv/ComputeCache:rw \
    -v ~/docker/isaac-sim/logs:/root/.nvidia-omniverse/logs:rw \
    -v ~/docker/isaac-sim/data:/root/.local/share/ov/data:rw \
    -v ~/docker/isaac-sim/documents:/root/Documents:rw \
    -v /home/{{ ansible_user }}/workspace:/workspace:rw \
    -v /home/{{ ansible_user }}/uploads:/uploads:rw \
    -v /home/{{ ansible_user }}/results:/results:rw \
    -p 8899:8899 \
    --env DISPLAY \
    --env XDG_RUNTIME_DIR=/tmp/runtime-isaac \
    --volume /tmp/.X11-unix:/tmp/.X11-unix:rw \
    --device /dev/dri \
    --env QT_X11_NO_MITSHM=1 \
    --volume /dev/input:/dev/input \
    --env XDG_CURRENT_DESKTOP=Unity \
    {{ isaac_image }} \
    -c "./runheadless.examples.sh"
