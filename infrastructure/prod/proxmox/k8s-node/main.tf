terraform {
  required_providers {
    proxmox = {
      source  = "bpg/proxmox"
      version = "~> 0.69"
    }
  }
}

resource "proxmox_virtual_environment_vm" "k8s_node" {
  name        = var.vm_name
  description = var.vm_description
  node_name   = var.proxmox_node

  dynamic "clone" {
    for_each = var.clone_template != "" ? [1] : []
    content {
      vm_id = tonumber(var.clone_template)
    }
  }

  cpu {
    cores   = var.cpu_cores
    sockets = var.cpu_sockets
  }

  memory {
    dedicated = var.memory
  }

  agent {
    enabled = true
  }

  boot_order = ["scsi0"]

  network_device {
    bridge = var.network_bridge
    model  = var.network_model
    vlan_id = var.vlan_tag != 0 ? var.vlan_tag : null
  }

  disk {
    datastore_id = var.storage_pool
    interface    = "scsi0"
    size         = parseint(regex("([0-9]+)", var.disk_size)[0], 10)
    file_format  = "raw"
  }

  dynamic "initialization" {
    for_each = var.ip_address != "" || var.ssh_keys != "" ? [1] : []
    content {
      datastore_id = var.storage_pool

      user_account {
        keys = var.ssh_keys != "" ? [var.ssh_keys] : []
        username = "ubuntu"
      }

      ip_config {
        ipv4 {
          address = var.ip_address != "" ? "${var.ip_address}/${var.ip_netmask}" : null
          gateway = var.ip_address != "" ? var.ip_gateway : null
        }
      }
    }
  }

  started = var.vm_state == "running"
  on_boot = true
}
