#!/bin/bash

# launch shell inside isaacsim contaner

docker run --name isaac-sim-shell --entrypoint bash -it --rm \
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
    {{ isaac_image }}
