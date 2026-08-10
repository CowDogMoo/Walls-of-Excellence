# Walls of Excellence

<div align="center">

<img src="./docs/images/logo.png" alt="Logo" align="center" width="144px" height="144px"/>

## My home operations repository :octocat:

_... managed with Flux, Renovate and GitHub Actions_ 🤖

</div>

<div align="center">

[![License](https://img.shields.io/github/license/CowDogMoo/Walls-of-Excellence?label=License&style=flat&color=blue&logo=github)](https://github.com/CowDogMoo/Walls-of-Excellence/blob/main/LICENSE)
[![Pre-Commit](https://github.com/CowDogMoo/Walls-of-Excellence/actions/workflows/pre-commit.yaml/badge.svg)](https://github.com/CowDogMoo/Walls-of-Excellence/actions/workflows/pre-commit.yaml)
[![Renovate](https://github.com/CowDogMoo/Walls-of-Excellence/actions/workflows/renovate.yaml/badge.svg)](https://github.com/CowDogMoo/Walls-of-Excellence/actions/workflows/renovate.yaml)

</div>

---

## 📖 Overview

**Walls of Excellence (woe)** is a home operations monorepo implementing
Infrastructure as Code (IaC) and GitOps practices for a multi-architecture
k3s cluster.

### Key Features

- **GitOps-Native**: Flux (flux-operator + flux-instance) reconciles
  everything under `kubernetes/apps/`
- **Automated Provisioning**: Ansible-based k3s deployment across Raspberry
  Pis, a Radxa ROCK 5B, and VM workers
- **Secrets Management**: External Secrets Operator backed by 1Password
- **Comprehensive Observability**: kube-prometheus-stack, Grafana, Loki,
  Tempo, Alloy, and Vector
- **Home Automation & Media**: Home Assistant, Frigate, Zigbee2MQTT,
  Music Assistant, and Immich
- **Security Testing**: Atomic Red Team, TTPForge, Sliver C2, and hashcat
- **CI/CD**: GitHub Actions (self-hosted runners via ARC) and Renovate

### Technology Stack

- **Kubernetes**: k3s
- **GitOps**: Flux CD (managed by flux-operator)
- **Provisioning**: Ansible
- **Package Management**: Helm, Helmfile
- **Secrets**: External Secrets Operator, 1Password
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
- [CI/CD](#cicd)
- [Resources](#resources)

---

## 📚 Documentation

<!-- BEGIN GENERATED: docs -->

- [Developer Environment Setup](docs/dev.md)
- [Rock5B NVMe Boot Setup](docs/rock5b-nvme-boot.md)
- [Test Environment](docs/test-environment.md)

<!-- END GENERATED: docs -->

For initial cluster setup, see the
[Bootstrap Instructions](kubernetes/bootstrap/README.md). Several
applications also carry a README next to their manifests under
[`kubernetes/apps/`](kubernetes/apps).

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
   git submodule update --init
   ```

2. **Set up development environment:**

   ```bash
   # Install pre-commit hooks
   task pre-commit:install-pre-commit-hooks

   # Authenticate with 1Password
   op signin
   ```

3. **Provision k3s cluster:**

   ```bash
   # Provision all nodes
   task provision

   # Wait for nodes to be ready
   task bootstrap:wait
   ```

4. **Bootstrap the cluster:**

   ```bash
   # Run complete bootstrap
   task bootstrap
   ```

5. **Verify Flux reconciliation:**

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
├── .github/          # CI workflows and Renovate configuration
├── .taskfiles/       # Local task definitions (bootstrap, test, ...)
├── docs/             # Guides and runbooks
├── hack/             # Utility scripts
├── infrastructure/   # Terraform/Terragrunt
├── k3s-ansible/      # Ansible k3s provisioning (git submodule)
└── kubernetes/
    ├── apps/         # Flux-managed applications, one directory per namespace
    ├── bootstrap/    # Initial cluster setup (helmfile.d, Flux install)
    ├── flux/         # Flux entry-point configuration
    └── deprecated/   # Retired configs kept for reference
```

---

## Cluster Architecture

### Nodes

- **Multi-architecture k3s cluster**: PoE-powered Raspberry Pis, a Radxa
  ROCK 5B (NVMe), and VM workers on Proxmox and macOS (Lima)
- **High Availability**: Multi-master control plane with embedded etcd
- **Control Plane VIP**: kube-vip

### Networking

- **Ingress**: Traefik with TLS termination
- **Load Balancing**: MetalLB for LoadBalancer services
- **DNS**: ExternalDNS with automatic record management, AdGuard Home for
  filtering
- **Remote Access**: Tailscale operator

### Storage

- **NFS**: Dynamic persistent volumes via nfs-subdir-external-provisioner,
  backed by a Synology NAS
- **Local**: local-path volumes for latency-sensitive workloads

### Data

- **PostgreSQL**: CloudNative-PG operator
- **MySQL**: Standalone instance

### Security

- **Secrets Management**: External Secrets Operator with 1Password
- **Authentication**: Authentik (OIDC provider)
- **Certificate Management**: cert-manager with Let's Encrypt

---

## Deployed Applications

<!-- BEGIN GENERATED: apps -->

Flux reconciles **48 applications** across **18 namespaces** from [`kubernetes/apps/`](kubernetes/apps).

| Namespace | Applications |
| --------- | ------------ |
| `actions-runner-system` | [actions-runner-controller](kubernetes/apps/actions-runner-system/actions-runner-controller) |
| `attack-simulation` | [ares](kubernetes/apps/attack-simulation/ares), [atomic-red-team](kubernetes/apps/attack-simulation/atomic-red-team), [ttpforge](kubernetes/apps/attack-simulation/ttpforge) |
| `c2` | [sliver](kubernetes/apps/c2/sliver) |
| `cert-manager` | [cert-manager](kubernetes/apps/cert-manager/cert-manager), [synology-cert-sync](kubernetes/apps/cert-manager/synology-cert-sync) |
| `cracking` | [hashcat](kubernetes/apps/cracking/hashcat) |
| `database` | [cloudnative-pg](kubernetes/apps/database/cloudnative-pg), [mysql](kubernetes/apps/database/mysql) |
| `external-secrets` | [external-secrets](kubernetes/apps/external-secrets/external-secrets), [onepassword](kubernetes/apps/external-secrets/onepassword) |
| `flux-system` | [addons](kubernetes/apps/flux-system/addons), [flux-instance](kubernetes/apps/flux-system/flux-instance), [flux-operator](kubernetes/apps/flux-system/flux-operator), [weave-gitops](kubernetes/apps/flux-system/weave-gitops) |
| `guacamole` | [guacamole](kubernetes/apps/guacamole/guacamole) |
| `home-automation` | [frigate](kubernetes/apps/home-automation/frigate), [grocy](kubernetes/apps/home-automation/grocy), [home-assistant](kubernetes/apps/home-automation/home-assistant), [mosquitto](kubernetes/apps/home-automation/mosquitto), [music-assistant](kubernetes/apps/home-automation/music-assistant), [printer-monitor](kubernetes/apps/home-automation/printer-monitor), [troy-backup](kubernetes/apps/home-automation/troy-backup), [zigbee2mqtt](kubernetes/apps/home-automation/zigbee2mqtt) |
| `identity` | [authentik](kubernetes/apps/identity/authentik) |
| `inference` | [ollama](kubernetes/apps/inference/ollama) |
| `kube-system` | [descheduler](kubernetes/apps/kube-system/descheduler), [nfs-subdir-external-provisioner](kubernetes/apps/kube-system/nfs-subdir-external-provisioner), [reflector](kubernetes/apps/kube-system/reflector), [reloader](kubernetes/apps/kube-system/reloader) |
| `media` | [immich](kubernetes/apps/media/immich) |
| `monitoring` | [runzero-explorer](kubernetes/apps/monitoring/runzero-explorer) |
| `networking` | [adguard-home](kubernetes/apps/networking/adguard-home), [external-dns](kubernetes/apps/networking/external-dns), [ingress-traefik](kubernetes/apps/networking/ingress-traefik), [tailscale-operator](kubernetes/apps/networking/tailscale-operator) |
| `observability` | [alloy](kubernetes/apps/observability/alloy), [blackbox-exporter](kubernetes/apps/observability/blackbox-exporter), [goldilocks](kubernetes/apps/observability/goldilocks), [grafana](kubernetes/apps/observability/grafana), [kube-prometheus-stack](kubernetes/apps/observability/kube-prometheus-stack), [loki](kubernetes/apps/observability/loki), [robusta](kubernetes/apps/observability/robusta), [tempo](kubernetes/apps/observability/tempo), [unpoller](kubernetes/apps/observability/unpoller), [vector](kubernetes/apps/observability/vector) |
| `system-upgrade` | [system-upgrade-controller](kubernetes/apps/system-upgrade/system-upgrade-controller) |

<!-- END GENERATED: apps -->

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
task check-inventory

# Reboot nodes
task reboot NODE=k8s1
task reboot-all

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

### Troubleshooting

```bash
# Remove stuck namespaces
task k8s:destroy-stuck-ns

# Reset cluster (destroy and rebuild)
task reset
task provision
task bootstrap
```

---

## Task Categories

The project uses [Task](https://taskfile.dev/). Remote categories are pulled
from [taskfile-templates](https://github.com/CowDogMoo/taskfile-templates)
at runtime; the first run prompts to trust them (or run `task -y`).

<!-- BEGIN GENERATED: tasks -->

Root tasks (run as `task <name>`): `default`, `check-inventory`,
`run-cmd-all`, `run-cmd`, `reboot`, `reboot-all`, `shutdown-cluster`, `ping`,
`ping-masters`, `ping-nodes`, `provision`, `provision-masters`,
`provision-nodes`, `reset`, `reset-masters`, `reset-nodes`, `apply-secrets`,
`destroy-rancher`, `reconcile`.

| Category | Defined in |
| -------- | ---------- |
| `ansible:*` | [CowDogMoo/taskfile-templates/ansible](https://github.com/CowDogMoo/taskfile-templates/blob/main/ansible/Taskfile.yaml) |
| `bootstrap:*` | [.taskfiles/bootstrap](.taskfiles/bootstrap/Taskfile.yaml) |
| `guacamole:*` | [.taskfiles/guacamole](.taskfiles/guacamole/Taskfile.yaml) |
| `k8s:*` | [CowDogMoo/taskfile-templates/k8s](https://github.com/CowDogMoo/taskfile-templates/blob/main/k8s/Taskfile.yaml) |
| `onepassword:*` | [CowDogMoo/taskfile-templates/secrets/onepassword](https://github.com/CowDogMoo/taskfile-templates/blob/main/secrets/onepassword/Taskfile.yaml) |
| `pre-commit:*` | [CowDogMoo/taskfile-templates/pre-commit](https://github.com/CowDogMoo/taskfile-templates/blob/main/pre-commit/Taskfile.yaml) |
| `proxmox:*` | [.taskfiles/proxmox](.taskfiles/proxmox/Taskfile.yaml) |
| `renovate:*` | [CowDogMoo/taskfile-templates/renovate](https://github.com/CowDogMoo/taskfile-templates/blob/main/renovate/Taskfile.yaml) |
| `terraform:*` | [CowDogMoo/taskfile-templates/terraform](https://github.com/CowDogMoo/taskfile-templates/blob/main/terraform/Taskfile.yaml) |
| `test:*` | [.taskfiles/test](.taskfiles/test/Taskfile.yaml) |

<!-- END GENERATED: tasks -->

Run `task -l` to see all available tasks with descriptions.

---

## CI/CD

### Automated Workflows

<!-- BEGIN GENERATED: workflows -->

- [Labeler](.github/workflows/meta-labeler.yaml)
- [Meta Sync labels](.github/workflows/meta-sync-labels.yaml)
- [Pre-Commit](.github/workflows/pre-commit.yaml)
- [🤖 Renovate](.github/workflows/renovate.yaml)
- [🚨 Semgrep Analysis](.github/workflows/semgrep.yaml)
- [🧪 Test Kubernetes Manifests](.github/workflows/test-manifests.yaml)

<!-- END GENERATED: workflows -->

### Renovate

Renovate automatically opens PRs for Helm chart, container image, GitHub
Action, and Flux component updates, using conventional commit messages and
custom managers for Flux and helm-values detection.

### README Generation

The application, documentation, task, and workflow listings in this README
are generated from repository state by
[`hack/readme-gen.sh`](hack/readme-gen.sh). A pre-commit hook keeps them
current — edit the source of truth (manifests, docs, taskfiles), not the
generated blocks.

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
- [External Secrets Operator](https://external-secrets.io/)
- [Ansible k3s Role](https://github.com/k3s-io/k3s-ansible)

### Community

- [Flux CD Slack](https://fluxcd.io/community/)
- [k3s GitHub Discussions](https://github.com/k3s-io/k3s/discussions)
- [Home Operations Discord](https://discord.gg/home-operations)

---

## License

See [LICENSE](LICENSE) file for details.
