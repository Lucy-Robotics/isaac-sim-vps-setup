# Vagrant Testing Environment

This directory contains the Vagrant-based testing environment for the Isaac Sim Ansible automation using KVM/libvirt virtualization.

## Quick Start

```bash
# 1. Install prerequisites (see TESTING.md for detailed instructions)
#    - Docker
#    - KVM/libvirt
#    - Vagrant with libvirt plugin

# 2. Run tests (Docker image will be built automatically)
./test-playbook.sh test
```

## Essential Commands

```bash
# Full test suite
./test-playbook.sh test

# Quick syntax check
./test-playbook.sh syntax

# Dry run (see what would change)
./test-playbook.sh dry-run

# Clean up VM
./test-playbook.sh cleanup
```

## Files

- `test-playbook.sh` - Main testing script with various commands
- `inventory` - Ansible inventory for test VM (auto-generated)
- `logs/` - Test execution logs (auto-created)

## Prerequisites Setup

**Important**: You need to manually install the prerequisites first. See [TESTING.md](../TESTING.md) for detailed setup instructions including:

- Docker installation
- KVM/libvirt installation
- Vagrant installation with libvirt plugin
- Troubleshooting common issues

## Documentation

See [TESTING.md](../TESTING.md) for complete documentation including:

- Detailed setup instructions for Linux
- KVM/libvirt configuration
- Advanced usage examples
- Troubleshooting guide
- Best practices

## VM Information

- **ansible-test**: GPU-ready testing VM (192.168.121.10)
  - Ubuntu 22.04 LTS
  - 6GB RAM, 4 CPUs
  - Desktop environment
  - Enhanced graphics support

VM uses:

- User: `vagrant`
- SSH key authentication (auto-configured)
- Port forwarding: SSH (2222), VNC (5900), RDP (3389)

## Why KVM/Libvirt Only?

This project uses KVM/libvirt as the only supported virtualization platform because:

- **Native Linux Integration**: Better performance and stability
- **No Licensing Issues**: Open source solution
- **Production Similarity**: Matches most Linux production environments
- **Active Development**: Continuously maintained by the Linux community
