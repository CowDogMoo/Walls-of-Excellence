# K8s8 Node

Kubernetes worker node configuration for Proxmox VM.

## Deploy

```bash
# From repo root
task proxmox:apply NODE=k8s8
```

## Configuration

Edit `terragrunt.hcl.tpl` to modify:

- IP address: `192.168.20.200`
- Resources: 4 cores, 8GB RAM, 100G disk
- Template: `ubuntu-2204-cloudinit-template`

SSH key auto-injected from 1Password: `op://automation/proxmox-ssh-key/public_key`

## After Creation

1. Add to `k3s-ansible/inventory/cowdogmoo/hosts.ini`
2. Run `task provision-nodes`
3. Verify with `kubectl get nodes`

See [parent README](../README.md) for detailed documentation.
