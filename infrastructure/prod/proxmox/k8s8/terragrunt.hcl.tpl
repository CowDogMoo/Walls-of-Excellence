include "root" {
  path = find_in_parent_folders("root.hcl")
}

terraform {
  source = "../k8s-node"
}

inputs = {
  vm_name        = "k8s8"
  vm_description = "Kubernetes worker node 8"
  proxmox_node   = "proxmox"

  # Clone from template (recommended) - comment out if creating from ISO
  clone_template = "9000"

  cpu_cores   = 2
  cpu_sockets = 1
  memory      = 8192  # 8GB in MB

  storage_pool = "local-lvm"  # Adjust based on your Proxmox storage
  disk_size    = "80G"
  disk_ssd     = false

  network_bridge = "vmbr0"
  network_model  = "virtio"
  vlan_tag       = 0  # Set to VLAN tag if needed

  # Static IP configuration (for cloud-init template)
  # Leave empty for DHCP
  ip_address = "192.168.20.200"
  ip_netmask = 24
  ip_gateway = "192.168.20.1"

  # SSH keys (for cloud-init template)
  # Injected from 1Password via op inject
  ssh_keys = "op://automation/proxmox-ssh-key/public_key"

  os_type = "l26"  # Linux 2.6+

  vm_state = "running"
}
