# Isaac Automator - Setup Host

A minimal tool for setting up remote SSH hosts with NVIDIA GPU support for Isaac Sim and Isaac Lab using Ansible automation.

## Overview

This is a streamlined version of Isaac Automator that focuses solely on configuring existing remote hosts via SSH, bypassing the need for cloud infrastructure provisioning. Perfect for on-premises setups, edge deployments, or when you already have GPU-enabled hosts available.

## Quick Start

### Prerequisites

- Docker and Docker Compose
- SSH access to target host with sudo privileges
- Host with NVIDIA GPU and Ubuntu 20.04/22.04
- NVIDIA Container Toolkit (NGC) API key

### Setup

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd lucy-isaac-automator
   ```

2. **Generate SSH key (if you don't have one)**

   ```bash
   # Generate a new SSH key in the project directory
   ssh-keygen -t ed25519 -f ./ssh_key -C "$(whoami)@isaac-automator-$(date +%Y%m%d)" -N ""
   ```

3. **Copy your public key to the target host**

   ```bash
   # Copy the public key to your target host
   ssh-copy-id -i ./ssh_key.pub SSH_USER@HOST_IP
   
   # Or manually add the public key content to ~/.ssh/authorized_keys on the target host
   cat ./ssh_key.pub
   ```

4. **Create environment configuration**

   ```bash
   cp .env.example .env
   ```

5. **Configure environment variables** (edit `.env`):

   ```bash
   # Required
   HOST_IP=192.168.1.100                    # Target host IP address  
   SSH_KEY_PATH=./ssh_key                   # SSH private key path (in project directory)
   NGC_API_KEY=your_ngc_api_key_here        # NVIDIA NGC API key

   # Optional (with defaults)
   SSH_USER=ubuntu                   # SSH username (e.g., ubuntu)
   DEPLOYMENT_NAME=my-deployment            # Deployment identifier (default: my-deployment)
   ```

6. **Setup the remote host**

   ```bash
   ./setup-host
   ```

The script will:

- Validate your NGC API key
- Configure the remote host with NVIDIA drivers
- Install Docker and NVIDIA Container Toolkit
- Set up Isaac Sim and Isaac Lab environments
- Create deployment state for management

## Management Commands

After successful setup, use these commands to manage your deployment:

```bash
# Connect to the remote host
./connect my-deployment

# Upload files to the remote host
./upload my-deployment --remote-dir /home/ubuntu/uploads

# Download results from the remote host
./download my-deployment --remote-dir /home/ubuntu/results

# Re-run Ansible configuration (repair)
./repair my-deployment

# Remove local deployment state
./destroy my-deployment
```

## Directory Structure

```
.
├── setup-host              # Main setup script
├── connect/upload/download  # Management scripts
├── .env                     # Environment configuration
├── ssh_key                  # SSH private key (you create this)
├── ssh_key.pub             # SSH public key (you create this)
├── src/
│   ├── ansible/            # Ansible playbooks and roles
│   └── python/             # Python utilities
└── state/                  # Deployment state (created during setup)
```

## User Account Management

This tool uses a **single-user approach** for simplicity:

- All operations (SSH connection, Isaac Sim, desktop environment) use your existing SSH user account
- No additional user accounts are created
- Your original user account remains completely unchanged
- Isaac Sim containers, file uploads/downloads, and remote desktop all use the same SSH user

This eliminates confusion between multiple user accounts and provides a clean, straightforward setup.

## SSH Key Management

### Creating SSH Keys

For security, place your SSH keys in the project directory (not your ~/.ssh/ folder) since only the project directory is mounted in the Docker container:

```bash
# Generate a new ed25519 SSH key in the project directory
ssh-keygen -t ed25519 -f ./ssh_key -C "$(whoami)@isaac-automator-$(date +%Y%m%d)" -N ""
```

### Key Setup Process

1. **Generate key in project directory** (as shown above)
2. **Copy public key to target host**:

   ```bash
   ssh-copy-id -i ./ssh_key.pub SSH_USER@YOUR_HOST_IP
   ```

3. **Test SSH connection**:

   ```bash
   ssh -i ./ssh_key SSH_USER@YOUR_HOST_IP
   ```

4. **Use `./ssh_key` in your .env file**

## Environment Configuration

The `.env` file supports these variables:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `HOST_IP` | ✓ | - | IP address of target host |
| `SSH_KEY_PATH` | ✓ | - | Path to SSH private key (use `./ssh_key`) |
| `NGC_API_KEY` | ✓ | - | NVIDIA NGC API key |
| `SSH_USER` | | ubuntu | SSH username |
| `DEPLOYMENT_NAME` | | my-deployment | Deployment identifier |

## Security Notes

- SSH keys in the project directory are excluded from Git (see .gitignore)
- The `.env` file contains sensitive information and is excluded from Git
- SSH keys should have appropriate permissions (600 for private, 644 for public)
- Store NGC API keys securely and rotate them regularly
- Never commit SSH keys or .env files to version control

## Troubleshooting

**SSH Key Issues:**

- Use `./ssh_key` (in project directory)
- Ensure key permissions: `chmod 600 ./ssh_key`
- Test SSH connection manually before running setup
- Verify public key is installed on target host

**Connection Issues:**

- Verify SSH key permissions and path
- Ensure target host is reachable and SSH is enabled
- Check that SSH user has sudo privileges

**GPU Setup Issues:**

- Verify host has compatible NVIDIA GPU
- Check Ubuntu version compatibility (20.04/22.04 recommended)
- Ensure sufficient disk space for containers

**Deployment Management:**

- Use `./repair <deployment>` to re-run configuration
- Check `state/<deployment>/` for deployment artifacts
- Use `--debug` flag for verbose output

## License

Licensed under the Apache License, Version 2.0
