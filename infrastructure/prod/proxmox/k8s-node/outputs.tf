output "vm_id" {
  description = "ID of the created VM"
  value       = proxmox_virtual_environment_vm.k8s_node.id
}

output "vm_name" {
  description = "Name of the created VM"
  value       = proxmox_virtual_environment_vm.k8s_node.name
}

output "vm_ip" {
  description = "IP address of the VM"
  value       = try(proxmox_virtual_environment_vm.k8s_node.ipv4_addresses[1][0], "")
}

output "ssh_host" {
  description = "SSH host for the VM"
  value       = var.ip_address != "" ? var.ip_address : try(proxmox_virtual_environment_vm.k8s_node.ipv4_addresses[1][0], "")
}

output "vm_config" {
  description = "VM configuration for inventory"
  value = {
    name     = proxmox_virtual_environment_vm.k8s_node.name
    ip       = var.ip_address != "" ? var.ip_address : try(proxmox_virtual_environment_vm.k8s_node.ipv4_addresses[1][0], "")
    cores    = var.cpu_cores
    memory   = var.memory
    disk     = var.disk_size
  }
}
