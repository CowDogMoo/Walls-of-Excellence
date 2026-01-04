variable "vm_name" {
  description = "Name of the VM (e.g., k8s8)"
  type        = string
}

variable "vm_description" {
  description = "Description of the VM"
  type        = string
  default     = "Kubernetes node"
}

variable "proxmox_node" {
  description = "Proxmox node to create the VM on"
  type        = string
  default     = "proxmox"
}

variable "clone_template" {
  description = "Name of the template to clone from (leave empty to create from scratch)"
  type        = string
  default     = ""
}

variable "cpu_cores" {
  description = "Number of CPU cores"
  type        = number
  default     = 4
}

variable "cpu_sockets" {
  description = "Number of CPU sockets"
  type        = number
  default     = 1
}

variable "memory" {
  description = "Amount of memory in MB"
  type        = number
  default     = 8192
}

variable "storage_pool" {
  description = "Storage pool for the VM disk"
  type        = string
  default     = "local-lvm"
}

variable "disk_size" {
  description = "Disk size (e.g., '100G')"
  type        = string
  default     = "100G"
}

variable "disk_ssd" {
  description = "Whether the disk is SSD"
  type        = bool
  default     = false
}

variable "network_bridge" {
  description = "Network bridge"
  type        = string
  default     = "vmbr0"
}

variable "network_model" {
  description = "Network model"
  type        = string
  default     = "virtio"
}

variable "vlan_tag" {
  description = "VLAN tag (0 for no VLAN)"
  type        = number
  default     = 0
}

variable "ip_address" {
  description = "Static IP address (leave empty for DHCP)"
  type        = string
  default     = ""
}

variable "ip_netmask" {
  description = "Network mask (e.g., 24)"
  type        = number
  default     = 24
}

variable "ip_gateway" {
  description = "Gateway IP address"
  type        = string
  default     = ""
}

variable "ssh_keys" {
  description = "SSH public keys for cloud-init"
  type        = string
  default     = ""
}

variable "os_type" {
  description = "OS type (e.g., 'l26' for Linux 2.6+)"
  type        = string
  default     = "l26"
}

variable "vm_state" {
  description = "Desired VM state (running or stopped)"
  type        = string
  default     = "running"

  validation {
    condition     = contains(["running", "stopped"], var.vm_state)
    error_message = "vm_state must be either 'running' or 'stopped'"
  }
}
