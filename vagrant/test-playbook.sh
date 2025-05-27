#!/bin/bash

# Ansible Vagrant Testing Script
# This script automates testing of the Ansible playbook against Vagrant VMs
# Uses the Docker container for unified Ansible environment and KVM/libvirt for VMs

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
VAGRANT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$VAGRANT_DIR")"
ANSIBLE_DIR="$PROJECT_ROOT/src/ansible"
INVENTORY_FILE="$VAGRANT_DIR/inventory"
PLAYBOOK_FILE="$ANSIBLE_DIR/isaac.yml"
LOG_DIR="$VAGRANT_DIR/logs"

# Docker configuration
DOCKER_IMAGE="isaac-automator"
DOCKER_CONTAINER_NAME="isaac-automator-test"

# Always use libvirt provider
VAGRANT_PROVIDER="libvirt"

# Create logs directory
mkdir -p "$LOG_DIR"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check if Vagrant is installed
    if ! command -v vagrant &> /dev/null; then
        print_error "Vagrant is not installed. Please install Vagrant first."
        exit 1
    fi
    
    # Check KVM/libvirt
    if ! command -v virsh &> /dev/null; then
        print_error "KVM/libvirt is not installed."
        print_error "Install it with: sudo apt-get install qemu-kvm libvirt-daemon-system libvirt-clients"
        exit 1
    fi
    
    if ! vagrant plugin list | grep -q vagrant-libvirt; then
        print_error "vagrant-libvirt plugin is not installed."
        print_error "Install it with: vagrant plugin install vagrant-libvirt"
        exit 1
    fi
    
    if ! systemctl is-active --quiet libvirtd; then
        print_error "libvirtd service is not running."
        print_error "Start it with: sudo systemctl start libvirtd"
        exit 1
    fi
    
    print_success "All prerequisites are installed (using KVM/libvirt provider)"
}

# Function to build Docker image if needed
ensure_docker_image() {
    print_status "Checking Docker image: $DOCKER_IMAGE"
    
    if ! docker image inspect "$DOCKER_IMAGE" &> /dev/null; then
        print_status "Building Docker image: $DOCKER_IMAGE"
        cd "$PROJECT_ROOT"
        docker build -t "$DOCKER_IMAGE" .
        print_success "Docker image built successfully"
    else
        print_status "Docker image $DOCKER_IMAGE already exists"
    fi
}

# Function to run command in Docker container
run_in_docker() {
    local cmd="$1"
    
    # Ensure we have the latest inventory
    generate_inventory
    
    # Run command in Docker container with proper volume mounts
    docker run --rm \
        --name "$DOCKER_CONTAINER_NAME" \
        --network host \
        -v "$PROJECT_ROOT:/app" \
        -v "$HOME/.ssh:/root/.ssh:ro" \
        -w /app \
        "$DOCKER_IMAGE" \
        bash -c "$cmd"
}

# Function to start VMs
start_vms() {
    local vm_name="$1"
    
    print_status "Starting VM: $vm_name (provider: libvirt)"
    cd "$PROJECT_ROOT"
    
    if vagrant status "$vm_name" | grep -q "running"; then
        print_warning "VM $vm_name is already running"
    else
        vagrant up --provider=libvirt "$vm_name"
        print_success "VM $vm_name started successfully"
    fi
    
    # Wait for SSH to be available
    print_status "Waiting for SSH to be available..."
    vagrant ssh "$vm_name" -c "echo 'SSH is ready'" || {
        print_error "Failed to connect to VM via SSH"
        exit 1
    }
    
    # Show connection information
    show_connection_info "$vm_name"
}

# Function to run Ansible playbook
run_playbook() {
    local target="$1"
    local timestamp=$(date +"%Y%m%d_%H%M%S")
    local log_file="$LOG_DIR/playbook_${target}_${timestamp}.log"
    
    print_status "Running Ansible playbook against $target using Docker container"
    print_status "Log file: $log_file"
    
    ensure_docker_image
    
    # Run the playbook with verbose output inside Docker container
    local ansible_cmd="cd src/ansible && ansible-playbook -i /app/vagrant/inventory -l $target isaac.yml -v"
    
    if run_in_docker "$ansible_cmd" 2>&1 | tee "$log_file"; then
        print_success "Playbook executed successfully against $target"
        show_connection_info "$target"
        return 0
    else
        print_error "Playbook execution failed against $target"
        print_error "Check log file: $log_file"
        return 1
    fi
}

# Function to run syntax check
syntax_check() {
    print_status "Running Ansible syntax check using Docker container..."
    
    ensure_docker_image
    
    local ansible_cmd="cd src/ansible && ansible-playbook --syntax-check -i /app/vagrant/inventory isaac.yml"
    
    if run_in_docker "$ansible_cmd"; then
        print_success "Syntax check passed"
    else
        print_error "Syntax check failed"
        exit 1
    fi
}

# Function to run dry run
dry_run() {
    local target="$1"
    
    print_status "Running dry run against $target using Docker container"
    
    ensure_docker_image
    
    local ansible_cmd="cd src/ansible && ansible-playbook -i /app/vagrant/inventory -l $target isaac.yml --check -v"
    
    if run_in_docker "$ansible_cmd"; then
        print_success "Dry run completed successfully"
    else
        print_error "Dry run failed"
        exit 1
    fi
}

# Function to cleanup
cleanup() {
    local vm_name="$1"
    
    print_status "Cleaning up VM: $vm_name"
    cd "$PROJECT_ROOT"
    
    vagrant halt "$vm_name" 2>/dev/null || true
    vagrant destroy -f "$vm_name" 2>/dev/null || true
    
    # Clean up Docker containers
    docker rm -f "$DOCKER_CONTAINER_NAME" 2>/dev/null || true
    
    print_success "Cleanup completed"
}

# Function to show provider info
show_provider_info() {
    print_status "Provider Information:"
    echo "  Current provider: ${VAGRANT_PROVIDER:-"auto-detect"}"
    echo ""
    
    if command -v docker &> /dev/null; then
        echo "  Docker: Available"
        if docker image inspect "$DOCKER_IMAGE" &> /dev/null; then
            echo "    - $DOCKER_IMAGE: Built"
        else
            echo "    - $DOCKER_IMAGE: Not built (will build automatically)"
        fi
    else
        echo "  Docker: Not available"
    fi
    
    if command -v virsh &> /dev/null; then
        echo "  KVM/libvirt: Available"
        if systemctl is-active --quiet libvirtd 2>/dev/null; then
            echo "    - libvirtd: Running"
        else
            echo "    - libvirtd: Not running"
        fi
        if vagrant plugin list | grep -q vagrant-libvirt; then
            echo "    - vagrant-libvirt: Installed"
        else
            echo "    - vagrant-libvirt: Not installed"
        fi
    else
        echo "  KVM/libvirt: Not available"
    fi
    
    echo ""
    echo "To set provider explicitly:"
    echo "  export VAGRANT_DEFAULT_PROVIDER=libvirt"
}

# Function to show usage
usage() {
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  start               Start the test VM"
    echo "  test                Run full test suite against VM"
    echo "  playbook            Run only the playbook against VM"
    echo "  syntax              Run syntax check only"
    echo "  dry-run             Run playbook in check mode"
    echo "  info                Show VM connection information"
    echo "  cleanup             Stop and destroy the VM"
    echo "  logs                Show recent log files"
    echo "  provider            Show provider information"
    echo "  build               Build Docker image"
    echo ""
    echo "Test VM:"
    echo "  ansible-test        Ubuntu 22.04 LTS with GPU support (6GB RAM, 4 CPUs)"
    echo ""
    echo "Environment:"
    echo "  - Ansible runs inside Docker container ($DOCKER_IMAGE)"
    echo "  - VM runs on KVM/libvirt with GPU-ready configuration"
    echo "  - SSH keys from ~/.ssh are mounted read-only"
    echo ""
    echo "Examples:"
    echo "  $0 test             # Run full test suite"
    echo "  $0 start            # Start VM and show connection info"
    echo "  $0 info             # Show connection information"
    echo "  $0 syntax           # Just check syntax"
    echo "  $0 cleanup          # Clean up VM"
    echo "  $0 build            # Build Docker image"
    echo ""
}

# Function to show logs
show_logs() {
    print_status "Recent log files:"
    ls -la "$LOG_DIR"/*.log 2>/dev/null | tail -5 || print_warning "No log files found"
}

# Function to generate dynamic inventory from Vagrant
generate_inventory() {
    local inventory_file="$VAGRANT_DIR/inventory"
    
    print_status "Generating dynamic inventory from Vagrant SSH config..."
    cd "$PROJECT_ROOT"
    
    # Create inventory header
    cat > "$inventory_file" << 'EOF'
[vagrant_vms]
EOF
    
    # Add running VMs to inventory with SSH details
    for vm in $(vagrant status --machine-readable | grep ",state," | grep ",running" | cut -d',' -f2); do
        # Get SSH config for this VM and handle line continuations
        local ssh_config=$(vagrant ssh-config "$vm" | tr -d '\n' | sed 's/  / /g')
        local hostname=$(echo "$ssh_config" | grep -o "HostName [^ ]*" | awk '{print $2}')
        local port=$(echo "$ssh_config" | grep -o "Port [^ ]*" | awk '{print $2}')
        local user=$(echo "$ssh_config" | grep -o "User [^ ]*" | awk '{print $2}')
        local key_file=$(echo "$ssh_config" | grep -o "IdentityFile [^ ]*" | awk '{print $2}')
        
        # Add VM to inventory with connection details (all on one line)
        echo "$vm ansible_host=$hostname ansible_port=$port ansible_user=$user ansible_ssh_private_key_file=$key_file" >> "$inventory_file"
    done
    
    # Add group mapping and variables
    cat >> "$inventory_file" << 'EOF'

# Map vagrant VMs to isaac group for playbook compatibility  
[isaac:children]
vagrant_vms

[vagrant_vms:vars]
ansible_ssh_common_args='-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null'
ansible_python_interpreter=/usr/bin/python3
ansible_connection=ssh

# Test variables - customize these for your testing needs
application_name=isaac-sim
deployment_name=test
ssh_port=2222
prompt_ansi_color=32
ngc_api_key_check=false

# NVIDIA variables (for GPU testing)
generic_driver_apt_package=nvidia-driver-470
EOF
    
    print_status "Generated inventory: $inventory_file"
}

# Function to build Docker image
build_docker_image() {
    print_status "Building Docker image: $DOCKER_IMAGE"
    cd "$PROJECT_ROOT"
    docker build -t "$DOCKER_IMAGE" .
    print_success "Docker image built successfully"
}

# Function to show VM connection information
show_connection_info() {
    local vm_name="$1"
    
    print_status "VM Connection Information:"
    echo ""
    echo "🖥️  VM Details:"
    echo "   Name: $vm_name"
    echo "   OS: Ubuntu 22.04 LTS"
    echo "   Resources: 6GB RAM, 4 CPUs"
    echo ""
    
    # Get VM IP address
    cd "$PROJECT_ROOT"
    local vm_ip=""
    if vagrant status "$vm_name" | grep -q "running"; then
        vm_ip=$(vagrant ssh "$vm_name" -c "hostname -I | awk '{print \$1}'" 2>/dev/null | tr -d '\r\n' || echo "Unable to detect")
    fi
    
    echo "🔐 Credentials:"
    echo "   Username: vagrant"
    echo "   Password: vagrant"
    echo "   SSH Key: Auto-configured (uses ~/.ssh keys)"
    echo ""
    
    echo "🌐 Network Access:"
    echo "   VM IP Address: ${vm_ip:-"192.168.121.10 (default)"}"
    echo ""
    
    echo "📡 Connection Methods:"
    echo ""
    echo "1️⃣  SSH Access:"
    echo "   # Via Vagrant (recommended):"
    echo "   vagrant ssh $vm_name"
    echo ""
    echo "   # Direct SSH:"
    echo "   ssh -p 2222 vagrant@localhost"
    echo "   # or if you know the VM IP:"
    echo "   ssh vagrant@${vm_ip:-"192.168.121.10"}"
    echo ""
    
    echo "2️⃣  VNC Access (Desktop):"
    echo "   # Install VNC viewer if needed:"
    echo "   sudo apt-get install tigervnc-viewer"
    echo ""
    echo "   # Connect via port forwarding:"
    echo "   vncviewer localhost:5900"
    echo "   # or directly to VM:"
    echo "   vncviewer ${vm_ip:-"192.168.121.10"}:5900"
    echo ""
    echo "   # VNC Password: (will be set during playbook execution)"
    echo ""
    
    echo "3️⃣  RDP Access (Desktop):"
    echo "   # Using rdesktop:"
    echo "   rdesktop localhost:3389"
    echo "   # or using freerdp:"
    echo "   xfreerdp /v:localhost:3389 /u:vagrant /p:vagrant"
    echo "   # or directly to VM:"
    echo "   xfreerdp /v:${vm_ip:-"192.168.121.10"}:3389 /u:vagrant /p:vagrant"
    echo ""
    
    echo "4️⃣  Web Access (if NoVNC is configured):"
    echo "   # Browser access:"
    echo "   http://localhost:6080/vnc.html"
    echo "   # or directly to VM:"
    echo "   http://${vm_ip:-"192.168.121.10"}:6080/vnc.html"
    echo ""
    
    echo "🔧 Useful Commands:"
    echo "   # Check VM status:"
    echo "   vagrant status"
    echo ""
    echo "   # Restart VM:"
    echo "   vagrant reload $vm_name"
    echo ""
    echo "   # Stop VM:"
    echo "   vagrant halt $vm_name"
    echo ""
    echo "   # Destroy VM:"
    echo "   vagrant destroy -f $vm_name"
    echo ""
    
    echo "📋 Port Forwarding (Host → VM):"
    echo "   SSH:  localhost:2222  → $vm_name:22"
    echo "   VNC:  localhost:5900  → $vm_name:5900"
    echo "   RDP:  localhost:3389  → $vm_name:3389"
    echo "   Web:  localhost:6080  → $vm_name:6080 (if configured)"
    echo ""
    
    print_success "VM is ready for connections!"
}

# Main execution
main() {
    local command=${1:-"help"}
    local vm_name="ansible-test"  # Single VM configuration
    
    case "$command" in
        "start")
            check_prerequisites
            start_vms "$vm_name"
            ;;
        "test")
            check_prerequisites
            start_vms "$vm_name"
            syntax_check
            dry_run "$vm_name"
            run_playbook "$vm_name"
            ;;
        "playbook")
            check_prerequisites
            ensure_docker_image
            run_playbook "$vm_name"
            ;;
        "syntax")
            check_prerequisites
            syntax_check
            ;;
        "dry-run")
            check_prerequisites
            dry_run "$vm_name"
            ;;
        "info")
            show_connection_info "$vm_name"
            ;;
        "cleanup")
            cleanup "$vm_name"
            ;;
        "logs")
            show_logs
            ;;
        "provider")
            show_provider_info
            ;;
        "build")
            build_docker_image
            ;;
        "help"|*)
            usage
            ;;
    esac
}

# Run main function with all arguments
main "$@" 