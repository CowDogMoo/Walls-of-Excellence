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

Walls of Excellence (woe) is a mono repository for my home
infrastructure and Kubernetes cluster which adheres to
Infrastructure as Code (IaC) and GitOps practices where possible

---

## Table of Contents

- [Developer Environment Setup](docs/dev.md)
- [Test Environment](docs/test-environment.md)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Usage](#usage)
- [Resources](#resources)

---

## Prerequisites

- [Task](https://taskfile.dev/installation/) - Task runner for automation
- [Flux CLI](https://fluxcd.io/flux/installation/) - GitOps toolkit
- [kubectl](https://kubernetes.io/docs/tasks/tools/) - Kubernetes CLI
- [Terraform](https://www.terraform.io/downloads) - Infrastructure as Code

### Quick Install (macOS)

```bash
brew install go-task/tap/go-task
brew install fluxcd/tap/flux
brew install kubectl
brew install terraform
```

---

## Installation

1. Clone the repository:

   ```bash
   gh repo clone CowDogMoo/Walls-of-Excellence woe
   cd woe
   ```

1. View available tasks:

   ```bash
   task -l
   ```

1. Bootstrap Flux (if you haven't already):

   ```bash
   export GITHUB_TOKEN=$FLUX_PAT
   export PATH_TO_FLUX_DEPLOYMENT=./kubernetes/flux-system/bootstrap-config
   export REPO_OWNER=CowDogMoo
   export REPO_NAME=Walls-of-Excellence

   flux bootstrap github \
     --owner=$REPO_OWNER \
     --repository=$REPO_NAME \
     --path=$PATH_TO_FLUX_DEPLOYMENT \
     --personal \
     --token-auth
   ```

1. Provision infrastructure:

   ```bash
   # Initialize and apply Terraform configurations
   task terraform:tf-apply
   ```

---

## Usage

### Cluster Management

```bash
# Provision k3s cluster
task provision

# Check cluster status
task ping

# Reboot all nodes
task reboot-all
```

### GitOps Operations

```bash
# Install Flux via Helm
task k8s:flux:install

# Reconcile Kubernetes resources
task reconcile

# Apply secrets
task apply-secrets
```

### Flux Synchronization

```bash
# Sync flux-system Kustomization with source
flux reconcile ks flux-system --with-source

# Sync cluster-apps Kustomization with source
flux reconcile ks cluster-apps --with-source -n flux-system
```

### Development Workflow

```bash
# Run pre-commit hooks
task pre-commit:run-pre-commit

# Lint Ansible playbooks
task ansible:lint-ansible

# Run Molecule tests
task ansible:run-molecule-tests

# Format and validate Terraform
task terraform:tf-check
```

### Troubleshooting

```bash
# Remove stuck namespaces
task k8s:destroy-stuck-ns

# Run command on all nodes
task run-cmd-all CMD="your-command"

# Reset cluster
task reset
```

---

## Task Categories

The project uses [Task](https://taskfile.dev/):

- **Root tasks**: Core cluster operations (provision, reconcile, reboot, etc.)
- `ansible:*`: Ansible automation and testing
- `k8s:*`: Kubernetes cluster management
- `terraform:*`: Infrastructure as Code operations
- `pre-commit:*`: Code quality and linting

Run `task -l` to see all available tasks with descriptions.

---

## Resources

This project was heavily influenced by the following:

- <https://github.com/onedr0p/home-ops/>
- <https://github.com/billimek/k8s-gitops>
