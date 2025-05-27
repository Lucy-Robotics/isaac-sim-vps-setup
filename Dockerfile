# Dockerfile for runnig and distributing the app

FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive
ENV force_color_prompt=yes

# paths for python
ENV PYTHONPATH=/app:/app/lib:/app/src:/app/py:/app/python:/app/cli:/app/utils:/app/tests

# misc
RUN apt-get update && apt-get install -qy \
    openssh-client \
    lsb-release \
    python3-pip \
    apt-utils \
    expect \
    unzip \
    rsync \
    curl \
    nano \
    wget \
    gpg \
    jq

# pip
RUN pip install click randomname pwgen debugpy

# ansible
ENV ANSIBLE_FORCE_COLOR=true
# for some reason, the ansible.cfg file is not being picked up on Windows
ENV ANSIBLE_CONFIG="/app/src/ansible/ansible.cfg"
RUN pip install ansible
RUN ansible-galaxy collection install community.docker

# ngc cli: https://docs.ngc.nvidia.com/cli/script.html
RUN cd /opt && wget https://ngc.nvidia.com/downloads/ngccli_cat_linux.zip && unzip ngccli_cat_linux.zip && rm ngccli_cat_linux.zip
RUN echo 'export PATH="$PATH:/opt/ngc-cli"' >> ~/.bashrc

# copy app code into container
COPY . /app

# customoize bash prompt
RUN echo "export PS1='\[\033[01;36m\][Isaac Automator \${VERSION}]\[\033[00m\]:\w\$ '" >>  /root/.bashrc

WORKDIR /app

ENTRYPOINT [ "/bin/sh", "-c" ]

ENV VERSION="v3.7.2"
