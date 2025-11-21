# Walls of Excellence

<div align="center">

<img src="./docs/images/logo.png" alt="Logo" align="center" width="144px" height="144px"/>

## My home operations repository :octocat:

_... managed with Flux, Renovate and GitHub Actions_ 🤖

</div>

<div align="center">

[![License](https://img.shields.io/github/license/CowDogMoo/Walls-of-Excellence?label=License&style=flat&color=blue&logo=github)](https://github.com/lCowDogMoo/Walls-of-Excellence/blob/main/LICENSE)
[![Pre-Commit](https://github.com/CowDogMoo/Walls-of-Excellence/actions/workflows/pre-commit.yaml/badge.svg)](https://github.com/CowDogMoo/Walls-of-Excellence/actions/workflows/pre-commit.yaml)
[![Renovate](https://github.com/CowDogMoo/Walls-of-Excellence/actions/workflows/renovate.yaml/badge.svg)](https://github.com/CowDogMoo/Walls-of-Excellence/actions/workflows/renovate.yaml)

</div>

---

## 📖 Overview

**Walls of Excellence (woe)** is a comprehensive home operations monorepo
implementing Infrastructure as Code (IaC) and GitOps practices for managing
a production-grade Kubernetes cluster.

### Key Features

- **GitOps-Native**: Flux CD for continuous deployment and reconciliation
- **Automated Provisioning**: Ansible-based k3s cluster deployment (7 nodes)
- **Secrets Management**: SOPS encryption with 1Password integration
- **Comprehensive Observability**: Prometheus, Grafana, Loki, and Alloy
- **Home Automation**: Home Assistant, MQTT, and smart home services
- **Security Testing**: Atomic Red Team, TTPForge, and C2 infrastructure
- **CI/CD**: Automated testing, validation, and dependency updates

### Technology Stack

- **Kubernetes**: k3s (lightweight, production-ready)
- **GitOps**: Flux CD v2.4.0+
- **Provisioning**: Ansible 2.11+
- **Package Management**: Helm, Helmfile
- **Secrets**: SOPS with age encryption, 1Password
- **Automation**: Task (go-task)
- **CI/CD**: GitHub Actions, Renovate

---

## Table of Contents

- [Overview](#-overview)
- [Documentation](#-documentation)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Repository Structure](#repository-structure)
- [Cluster Architecture](#cluster-architecture)
- [Deployed Applications](#deployed-applications)
- [Usage](#usage)
- [Task Categories](#task-categories)
- [Resources](#resources)

---

## 📚 Documentation

- **[Developer Environment Setup](docs/dev.md)** - Complete development
  workflow guide
- **[Test Environment](docs/test-environment.md)** - Local testing with
  kind clusters
- **[Bootstrap Instructions](kubernetes/bootstrap/README.md)** - Initial
  cluster setup

---

## Prerequisites

### Required Tools

- **[Task](https://taskfile.dev/installation/)** - Task runner for automation
- **[Flux CLI](https://fluxcd.io/flux/installation/)** - GitOps toolkit
- **[kubectl](https://kubernetes.io/docs/tasks/tools/)** - Kubernetes CLI
- **[Helm](https://helm.sh/docs/intro/install/)** - Package manager
- **[Helmfile](https://helmfile.readthedocs.io/)** - Helm release orchestrator
- **[Kustomize](https://kubectl.docs.kubernetes.io/installation/kustomize/)**
  \- Manifest customization
- **[yq](https://github.com/mikefarah/yq)** - YAML processor
- **[age](https://github.com/FiloSottile/age)** - Encryption tool
- **[1Password CLI](https://developer.1password.com/docs/cli/)** - Secret
  management
- **[Ansible](https://docs.ansible.com/ansible/latest/installation_guide/intro_installation.html)**
  \- Infrastructure provisioning
- **[Terraform](https://www.terraform.io/downloads)** - Infrastructure as Code

### Quick Install (macOS)

```bash
brew install go-task/tap/go-task
brew install fluxcd/tap/flux
brew install kubectl
brew install helm
brew install helmfile
brew install kustomize
brew install yq
brew install age
brew install ansible
brew install terraform
brew install --cask 1password-cli
```

### Quick Install (Linux)

See [Developer Guide](docs/dev.md) for detailed Linux installation instructions.

---

## Quick Start

### For New Clusters

1. **Clone the repository:**

   ```bash
   gh repo clone CowDogMoo/Walls-of-Excellence woe
   cd woe
   ```

2. **Set up development environment:**

   ```bash
   # Install pre-commit hooks
   task pre-commit:install-pre-commit-hooks

   # Authenticate with 1Password
   op signin
   ```

3. **Configure SOPS encryption:**

   ```bash
   # Generate age key
   age-keygen -o keys.txt

   # Store private key in 1Password
   # Add public key to .sops.yaml
   ```

4. **Provision k3s cluster:**

   ```bash
   # Provision all nodes
   task provision

   # Wait for nodes to be ready
   task bootstrap:wait
   ```

5. **Bootstrap the cluster:**

   ```bash
   # Run complete bootstrap
   task bootstrap
   ```

6. **Verify Flux reconciliation:**

   ```bash
   flux get kustomizations -A
   ```

### For Existing Clusters

```bash
# Check cluster status
task ping

# View available tasks
task -l

# Reconcile configurations
task reconcile

# Apply secrets
task apply-secrets
```

---

## Repository Structure

```text
woe/
├── .github/                    # GitHub Actions workflows
│   ├── workflows/              # CI/CD pipelines
│   └── renovate/               # Dependency update configs
├── .taskfiles/                 # Task definitions
│   ├── bootstrap/              # Bootstrap tasks
│   └── test/                   # Testing tasks
├── docs/                       # Documentation
│   ├── dev.md                  # Development guide
│   └── test-environment.md     # Testing guide
├── hack/                       # Utility scripts
├── infrastructure/             # Terraform/Terragrunt
├── k3s-ansible/                # Ansible k3s provisioning
│   ├── inventory/cowdogmoo/    # 7-node inventory
│   ├── roles/                  # Ansible roles
│   ├── molecule/               # Testing scenarios
│   ├── site.yml                # Main playbook
│   └── reset.yml               # Teardown playbook
├── kubernetes/
│   ├── apps/                   # 16 namespaces, 35+ apps
│   │   ├── attack-simulation/  # Red team tools
│   │   ├── c2/                 # Command & control
│   │   ├── cert-manager/       # TLS management
│   │   ├── database/           # MySQL
│   │   ├── external-secrets/   # Secret sync
│   │   ├── flux-system/        # Flux components
│   │   ├── guacamole/          # Remote desktop
│   │   ├── home-automation/    # Smart home services
│   │   ├── identity/           # Authentik (OIDC)
│   │   ├── kube-system/        # System components
│   │   ├── monitoring/         # RunZero
│   │   ├── networking/         # Traefik, ExternalDNS
│   │   ├── observability/      # Grafana, Loki, Prometheus
│   │   └── system-upgrade/     # Upgrade controller
│   ├── bootstrap/              # Initial setup
│   │   ├── flux/               # Flux CRDs
│   │   ├── helmfile.d/         # Helmfile configs
│   │   └── resources.yaml.j2   # Secret templates
│   ├── flux/                   # Flux GitOps configs
│   └── deprecated/             # Legacy configs (skipped)
├── .sops.yaml                  # SOPS encryption rules
├── ansible.cfg                 # Ansible configuration
└── Taskfile.yaml               # Root task definitions
```

---

## Cluster Architecture

### Nodes

- **7-node cluster**: k8s1 through k8s7
- **High Availability**: Multi-master control plane with etcd
- **Load Balancing**: kube-vip (control plane), MetalLB (services)
- **CNI Options**: Calico or Cilium (configurable)

### Networking

- **Cluster CIDR**: 10.52.0.0/16
- **Service CIDR**: 10.53.0.0/16
- **Load Balancer Range**: 192.168.30.80-192.168.30.90
- **Ingress**: Traefik with TLS termination
- **DNS**: External DNS with automatic record management

### Storage

- **NFS Provisioner**: Dynamic persistent volume provisioning
- **Persistent Volumes**: Backed by NFS server

### Security

- **Secrets Encryption**: SOPS with age
- **Authentication**: Authentik (OIDC provider)
- **Certificate Management**: cert-manager with Let's Encrypt
- **Network Policies**: Calico/Cilium network policies

---

## Deployed Applications

### System & Infrastructure

- **NFS Subdir External Provisioner** - Dynamic PVC provisioning
- **Reflector** - ConfigMap/Secret mirroring
- **Reloader** - Auto-restart on config changes
- **System Upgrade Controller** - Coordinated node upgrades

### GitOps & Deployment

- **Flux Operator** - Flux cluster management
- **Flux Instance** - Git synchronization
- **Weave GitOps** - Flux UI

### Security & Identity

- **Authentik** - OIDC authentication provider
- **cert-manager** - TLS certificate lifecycle
- **external-secrets** - 1Password integration
- **Guacamole** - Remote desktop gateway

### Network Services

- **Traefik** - Ingress controller
- **External DNS** - DNS automation

### Observability

- **Prometheus** - Metrics collection
- **Grafana** - Visualization and dashboards
- **Loki** - Log aggregation
- **Alloy** - Telemetry collection
- **Vector** - Log processing
- **AlertManager** - Alert routing
- **Unpoller** - UniFi metrics

### Home Automation

- **Home Assistant** - Home automation platform
- **Mosquitto** - MQTT broker
- **Music Assistant** - Music server
- **Grocy** - Inventory management
- **Printer Monitor** - Printer status monitoring

### Security Testing

- **Atomic Red Team** - Attack simulation
- **TTPForge** - Threat modeling
- **Sliver** - C2 framework

### Monitoring

- **RunZero Explorer** - Network discovery

### Database

- **MySQL** - SQL database backend

---

## Usage

### Cluster Management

```bash
# Provision entire k3s cluster
task provision

# Provision specific node groups
task provision-masters
task provision-nodes

# Check cluster status
task ping
task ping-masters
task ping-nodes

# Reboot nodes
task reboot NODE=k8s1
task reboot-all
```

### Node Operations

```bash
# Run command on all nodes
task run-cmd-all -- 'uptime'

# Run command on specific node
task run-cmd NODE=k8s1 -- 'df -h'
```

### GitOps Operations

```bash
# Bootstrap cluster from scratch
task bootstrap

# Individual bootstrap steps
task bootstrap:wait        # Wait for nodes
task bootstrap:namespaces  # Create namespaces
task bootstrap:resources   # Apply secrets
task bootstrap:crds        # Apply CRDs
task bootstrap:apps        # Deploy core apps

# Reconcile Kubernetes resources
task reconcile

# Apply secrets
task apply-secrets
```

### Flux Synchronization

```bash
# Sync Flux system
flux reconcile ks flux-system --with-source

# Sync cluster apps
flux reconcile ks cluster-apps --with-source -n flux-system

# Check Flux status
flux get all -A

# View Flux logs
flux logs --all-namespaces --follow
```

### Development Workflow

```bash
# View all available tasks
task -l

# Run pre-commit hooks
task pre-commit:run-pre-commit

# Validate manifests locally
task test:validate

# Test in kind cluster
task test:create
task test:install-flux
task test:apply
task test:status
task test:destroy
```

### Ansible Operations

```bash
# Lint Ansible playbooks
task ansible:lint-ansible

# Run Molecule tests
task ansible:run-molecule-tests

# List Ansible hosts
task ansible:list-hosts
```

### Terraform Operations

```bash
# Format and validate
task terraform:tf-check

# Plan infrastructure changes
task terraform:tf-plan

# Apply infrastructure changes
task terraform:tf-apply
```

### Troubleshooting

```bash
# Remove stuck namespaces
task k8s:destroy-stuck-ns

# Completely remove Rancher (if installed)
task destroy-rancher

# Reset cluster (destroy and rebuild)
task reset
task reset-masters
task reset-nodes
```

---

## Task Categories

The project uses [Task](https://taskfile.dev/) with the following categories:

| Category | Description | Example Tasks |
| -------- | ----------- | ------------- |
| **Root tasks** | Core cluster operations | `provision`, `ping` |
| `ansible:*` | Ansible automation/testing | `ansible:lint-ansible` |
| `k8s:*` | Kubernetes management | `k8s:destroy-stuck-ns` |
| `terraform:*` | Infrastructure as Code | `terraform:tf-check` |
| `pre-commit:*` | Code quality/linting | `pre-commit:run-pre-commit` |
| `renovate:*` | Renovate bot operations | `renovate:dry-run` |
| `bootstrap:*` | Cluster bootstrap | `bootstrap:wait` |
| `test:*` | Local testing with kind | `test:create`, `test:apply` |

Run `task -l` to see all available tasks with descriptions.

---

## CI/CD

### Automated Workflows

- **Pre-commit**: Runs on every commit and PR
- **Test Manifests**: Validates and tests deployments in kind clusters
- **Renovate**: Weekly dependency updates (Sunday & Wednesday 00:00 UTC)
- **Semgrep**: Security linting

### Renovate Features

- **Semantic commits**: Follows conventional commit format
- **Auto-merge**: Digest updates and branch creation
- **Custom managers**: Flux and helm-values detection
- **Pre-commit integration**: Runs hooks on update PRs

View workflow runs:

```bash
gh run list
gh run view <run-id>
gh run watch
```

---

## Maintenance

### Regular Updates

Renovate automatically creates PRs for:

- Helm chart updates
- Docker image updates
- GitHub Action updates
- Flux component updates

### Manual Updates

```bash
# Update Flux
flux install --export > kubernetes/bootstrap/flux/gotk-components.yaml

# Update CRDs
task bootstrap:crds

# Reconcile changes
flux reconcile ks flux-system --with-source
```

### Cluster Reset

If the cluster becomes unrecoverable:

```bash
# Complete cluster reset and rebuild
task reset          # Reset k3s cluster
task provision      # Reprovision with Ansible
task bootstrap      # Bootstrap from scratch
flux get ks -A      # Verify reconciliation
```

---

## Resources

### Inspiration

This project was influenced by:

- <https://github.com/onedr0p/home-ops/>
- <https://github.com/billimek/k8s-gitops>

### Documentation

- [Flux CD Documentation](https://fluxcd.io/flux/)
- [k3s Documentation](https://docs.k3s.io/)
- [Task Documentation](https://taskfile.dev/)
- [SOPS Documentation](https://github.com/getsops/sops)
- [Ansible k3s Role](https://github.com/k3s-io/k3s-ansible)

### Community

- [Flux CD Slack](https://fluxcd.io/community/)
- [k3s GitHub Discussions](https://github.com/k3s-io/k3s/discussions)
- [Home Operations Discord](https://discord.gg/home-operations)

---

## License

See [LICENSE](LICENSE) file for details.
