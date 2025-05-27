# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  config.vm.box = "generic/ubuntu2204"  # Ubuntu 22.04 LTS
  
  # Single VM Configuration for GPU Testing
  config.vm.define "ansible-test" do |vm|
    vm.vm.hostname = "ansible-test"
    
    # Network configuration for libvirt
    vm.vm.network "private_network", type: "dhcp"
    vm.vm.network "forwarded_port", guest: 22, host: 2222, id: "ssh"
    vm.vm.network "forwarded_port", guest: 5900, host: 5900, id: "vnc"  # VNC
    vm.vm.network "forwarded_port", guest: 3389, host: 3389, id: "rdp"  # RDP
    
    # Libvirt provider configuration - GPU-ready VM
    vm.vm.provider "libvirt" do |libvirt|
      libvirt.memory = 6144  # 6GB RAM for GPU testing
      libvirt.cpus = 4
      libvirt.graphics_type = "spice"
      libvirt.graphics_autoport = "yes"
      libvirt.video_type = "qxl"
      libvirt.video_vram = 256
      
      # Enable nested virtualization and better CPU features
      libvirt.nested = true
      libvirt.cpu_mode = "host-passthrough"
    end
    
    # Provisioning for GPU-ready environment
    vm.vm.provision "shell", inline: <<-SHELL
      # Update system
      apt-get update
      
      # Install Python for Ansible
      apt-get install -y python3 python3-pip python3-dev
      
      # Install desktop environment for GUI testing
      apt-get install -y ubuntu-desktop-minimal
      
      # Install basic dependencies
      apt-get install -y curl wget git build-essential
      
      echo "GPU-ready VM provisioning complete!"
    SHELL
  end
end 