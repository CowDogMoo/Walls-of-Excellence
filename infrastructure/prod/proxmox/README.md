# Proxmox Infrastructure

Terraform/Terragrunt configurations for provisioning Kubernetes nodes on
Proxmox VE. Create, update, and manage VMs using infrastructure as code with
automated secret injection from 1Password.

## Quick Start

```bash
# Create a new K8s node (complete workflow)
task proxmox:create NODE=k8s9 IP=192.168.20.201
```

## Setup

### 1. Install Tools

```bash
brew install terraform terragrunt 1password-cli
eval $(op signin)
```

### 2. Configure Environment

Add to `~/.zshrc` or `~/.bashrc`:

```bash
export PM_API_URL="https://proxmox:8006/api2/json"
export PM_API_TOKEN_ID="terraform@pam!mytoken"
export PM_API_TOKEN_SECRET="your-secret-here"
export TASK_X_REMOTE_TASKFILES=1
```

### 3. Create Proxmox API Token

```bash
ssh proxmox
pveum user add terraform@pam
pveum user token add terraform@pam mytoken --privsep=0
pveum acl modify / --roles PVEVMAdmin --users terraform@pam
```

## Cloud-Init Template (Optional)

Creating VMs from a cloud-init template is faster than ISO installation:

```bash
ssh proxmox
cd /var/lib/vz/template/iso
wget https://cloud-images.ubuntu.com/jammy/current/jammy-server-cloudimg-amd64.img

VM_ID=9000
qm create $VM_ID --name ubuntu-2204-cloudinit-template --memory 2048 --cores 2 --net0 virtio,bridge=vmbr0
qm importdisk $VM_ID jammy-server-cloudimg-amd64.img local-lvm
qm set $VM_ID --scsihw virtio-scsi-pci --scsi0 local-lvm:vm-$VM_ID-disk-0
qm set $VM_ID --ide2 local-lvm:cloudinit
qm set $VM_ID --boot c --bootdisk scsi0
qm set $VM_ID --serial0 socket --vga serial0
qm set $VM_ID --agent enabled=1
qm resize $VM_ID scsi0 +98G
qm template $VM_ID
```

## Usage

### Create a Node

```bash
task proxmox:create NODE=k8s9 IP=192.168.20.201
```

### Common Tasks

```bash
task proxmox:plan NODE=k8s8    # Preview changes
task proxmox:apply NODE=k8s8   # Apply changes
task proxmox:output NODE=k8s8  # Show VM details
task proxmox:destroy NODE=k8s8 # Remove VM
task proxmox:clean NODE=k8s8   # Clean generated files
task proxmox                   # List all tasks
```

### Manual Method

```bash
cd infrastructure/prod/proxmox/k8s8
op inject -i terragrunt.hcl.tpl -o terragrunt.hcl
terragrunt init
terragrunt plan
terragrunt apply
```

## Configuration

Key variables in `terragrunt.hcl.tpl`:

| Variable | Default | Description |
| -------- | ------- | ----------- |
| `vm_name` | - | Node name (required) |
| `ip_address` | `""` | Static IP (empty = DHCP) |
| `clone_template` | `""` | Template to clone |
| `cpu_cores` | `4` | CPU cores |
| `memory` | `8192` | RAM in MB |
| `disk_size` | `"100G"` | Disk size |
| `storage_pool` | `"local-lvm"` | Storage pool |

Full module documentation in `k8s-node/README.md`.

## Post-Creation

1. **Add to Ansible inventory** (`k3s-ansible/inventory/cowdogmoo/hosts.ini`)
2. **Provision**: `task provision-nodes`
3. **Verify**: `kubectl get nodes`

## Troubleshooting

```bash
# Test API access
env | grep PM_
curl -k -H "Authorization: PVEAPIToken=${PM_API_TOKEN_ID}=${PM_API_TOKEN_SECRET}" ${PM_API_URL}/version

# List templates
ssh proxmox "qm list | grep template"

# Check storage
ssh proxmox pvesm status

# Test 1Password CLI
op item get "proxmox-ssh-key" --vault automation

# Verify cloud-init
ssh proxmox qm cloudinit dump <vmid> user
```

## Resources

- [Telmate Proxmox Provider](https://registry.terraform.io/providers/Telmate/proxmox/latest/docs)
- [Proxmox API](https://pve.proxmox.com/pve-docs/api-viewer/)
- [Terragrunt Docs](https://terragrunt.gruntwork.io/)
