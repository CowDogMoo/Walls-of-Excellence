# Developer Environment Setup

To get involved with this project,
[create a fork](https://docs.github.com/en/get-started/quickstart/fork-a-repo)
and follow along.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Dependencies](#dependencies)
- [Configure Environment](#configure-environment)
- [Development Workflow](#development-workflow)
- [Cluster Operations](#cluster-operations)
- [Debugging](#debugging)
- [Testing](#testing)

---

## Prerequisites

This project requires:

- **Linux or macOS** - Development environment
- **SSH access** - To cluster nodes (k8s1-k8s7)
- **1Password CLI** - For secrets management
- **age** - For SOPS encryption

---

## Dependencies

### Core Tools

Install via Homebrew:

```bash
# Install homebrew first (if not already installed)
# Linux
sudo apt-get update
sudo apt-get install -y build-essential procps curl file git
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"

# macOS
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

```bash
# Install required tools
brew install go-task/tap/go-task
brew install fluxcd/tap/flux
brew install kubectl
brew install kustomize
brew install helmfile
brew install helm
brew install yq
brew install age
brew install pre-commit
brew install ansible
brew install terraform
brew install terragrunt
```

### Optional Tools

```bash
# For local testing
brew install kind

# For 1Password CLI
brew install --cask 1password-cli
```

### Python Dependencies

```bash
# For Ansible and utility scripts
python3 -m pip install --upgrade pip
python3 -m pip install ansible kubernetes
```

---

## Configure Environment

### 1. Clone the Repository

```bash
gh repo clone CowDogMoo/Walls-of-Excellence woe
cd woe
```

### 2. Install Pre-commit Hooks

```bash
task pre-commit:install-pre-commit-hooks
```

### 3. Update Pre-commit Hooks

```bash
task pre-commit:run-pre-commit
```

### 4. Set Up 1Password

Authenticate with 1Password CLI:

```bash
op signin
```

Verify authentication:

```bash
op whoami
```

### 5. Configure SOPS (First-Time Setup Only)

For a new cluster, generate age encryption keys:

```bash
# Generate age key
age-keygen -o keys.txt

# Store private key in 1Password
# Item: kubernetes/sops
# Field: SOPS_PRIVATE_KEY

# Add public key to .sops.yaml
```

See [kubernetes/bootstrap/README.md](../kubernetes/bootstrap/README.md)
for detailed SOPS setup.

---

## Development Workflow

### Daily Development

```bash
# Check cluster status
task ping

# View available tasks
task -l

# Run pre-commit checks before committing
task pre-commit:run-pre-commit

# Validate manifests locally
task test:validate
```

### Making Changes

1. **Create a feature branch:**

   ```bash
   git checkout -b feature/my-change
   ```

2. **Test locally** (see [Testing](#testing) section)

3. **Run pre-commit:**

   ```bash
   task pre-commit:run-pre-commit
   ```

4. **Commit changes:**

   ```bash
   git add .
   git commit -m "feat: add my feature"
   ```

5. **Push and create PR:**

   ```bash
   git push origin feature/my-change
   gh pr create
   ```

### Code Quality

Pre-commit hooks automatically check:

- YAML syntax (yamllint)
- Shell scripts (shellcheck, shfmt)
- Markdown (markdownlint)
- Spelling (codespell)
- JSON/YAML formatting (prettier)
- File permissions
- Trailing whitespace

Run manually:

```bash
task pre-commit:run-pre-commit
```

---

## Cluster Operations

### Provisioning

```bash
# Provision entire cluster
task provision

# Provision only master nodes
task provision-masters

# Provision only worker nodes
task provision-nodes
```

### Node Management

```bash
# Ping all nodes
task ping

# Ping masters only
task ping-masters

# Ping workers only
task ping-nodes

# Run command on all nodes
task run-cmd-all -- 'uptime'

# Run command on specific node
task run-cmd NODE=k8s1 -- 'df -h'

# Reboot specific node
task reboot NODE=k8s1

# Reboot all nodes (with confirmation)
task reboot-all
```

### Kubernetes Operations

```bash
# Apply Kubernetes configurations
task reconcile

# Apply secrets
task apply-secrets

# Bootstrap cluster from scratch
task bootstrap

# Individual bootstrap steps
task bootstrap:wait        # Wait for nodes
task bootstrap:namespaces  # Create namespaces
task bootstrap:resources   # Apply secrets
task bootstrap:crds        # Apply CRDs
task bootstrap:apps        # Deploy core apps
```

### Flux Operations

```bash
# Reconcile Flux system
flux reconcile ks flux-system --with-source

# Reconcile cluster apps
flux reconcile ks cluster-apps --with-source -n flux-system

# Check Flux status
flux get all -A

# View Flux logs
flux logs --all-namespaces --follow
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

# Plan changes
task terraform:tf-plan

# Apply changes
task terraform:tf-apply
```

---

## Debugging

### Flux Debugging

The official Flux cheatsheet has useful debugging commands:
<https://fluxcd.io/flux/cheatsheets/troubleshooting/>

```bash
# Check Kustomization status
flux get kustomizations -A

# Check HelmRelease status
flux get helmreleases -A

# View Kustomization events
kubectl describe kustomization <name> -n flux-system

# View HelmRelease events
kubectl describe helmrelease <name> -n <namespace>

# Check Flux controller logs
kubectl logs -n flux-system deploy/source-controller
kubectl logs -n flux-system deploy/kustomize-controller
kubectl logs -n flux-system deploy/helm-controller
```

### Cluster Debugging

```bash
# Check pod status
kubectl get pods -A

# View recent events
kubectl get events -A --sort-by='.lastTimestamp'

# Check node status
kubectl get nodes -o wide

# View node resources
kubectl top nodes

# Check persistent volumes
kubectl get pv,pvc -A
```

### Application Debugging

```bash
# View pod logs
kubectl logs <pod-name> -n <namespace>

# Follow logs
kubectl logs -f <pod-name> -n <namespace>

# Describe pod
kubectl describe pod <pod-name> -n <namespace>

# Execute into pod
kubectl exec -it <pod-name> -n <namespace> -- /bin/sh

# View service endpoints
kubectl get endpoints -n <namespace>
```

### Cleanup Stuck Resources

```bash
# Remove stuck namespaces
task k8s:destroy-stuck-ns

# Completely remove Rancher (if installed)
task destroy-rancher
```

---

## Testing

### Local Testing with kind

See [test-environment.md](test-environment.md) for comprehensive testing documentation.

Quick start:

```bash
# Validate manifests
task test:validate

# Create test cluster
task test:create

# Install Flux
task test:install-flux

# Apply configurations
task test:apply

# Check status
task test:status

# Destroy cluster
task test:destroy
```

### Testing Specific Apps

```bash
# Test single app
task test:apply-app APP=cert-manager

# Create mock secrets for testing
task test:mock-secrets
task test:mock-secrets NAMESPACE=home-automation
```

### CI/CD Testing

GitHub Actions automatically:

1. Validates manifests on every commit
2. Tests deployments in kind clusters
3. Runs pre-commit hooks
4. Performs security scanning (Semgrep)

View workflow runs:

```bash
gh run list
gh run view <run-id>
```

---

## Destroy and Rebuild the Cluster

If the cluster becomes unrecoverable, completely rebuild:

```bash
# 1. Reset the entire cluster
task reset

# 2. Reprovision with Ansible
task provision

# 3. Wait for nodes to be ready
task bootstrap:wait

# 4. Run complete bootstrap
task bootstrap

# 5. Verify Flux reconciliation
flux get kustomizations -A
```

Or reset specific node groups:

```bash
# Reset and rebuild masters
task reset-masters
task provision-masters

# Reset and rebuild workers
task reset-nodes
task provision-nodes
```

---

## Repository Structure

```text
woe/
├── .github/              # GitHub Actions workflows
├── .taskfiles/           # Task definitions (bootstrap, test)
├── docs/                 # Documentation
├── infrastructure/       # Terraform/Terragrunt configs
├── k3s-ansible/          # Ansible k3s provisioning
│   ├── inventory/        # Cluster inventory (7 nodes)
│   ├── roles/            # Ansible roles
│   └── site.yml          # Main playbook
├── kubernetes/
│   ├── apps/             # Application manifests (16 namespaces)
│   ├── bootstrap/        # Bootstrap configuration
│   │   ├── flux/         # Flux CRDs and components
│   │   ├── helmfile.d/   # Helmfile configs
│   │   └── resources.yaml.j2  # Secret templates
│   └── flux/             # Flux GitOps configs
├── .sops.yaml            # SOPS encryption rules
├── ansible.cfg           # Ansible configuration
└── Taskfile.yaml         # Root task definitions
```

---

## Resources

- [Main README](../README.md)
- [Test Environment Guide](test-environment.md)
- [Bootstrap Instructions](../kubernetes/bootstrap/README.md)
- [Flux Documentation](https://fluxcd.io/flux/)
- [Task Documentation](https://taskfile.dev/)
- [Ansible k3s Role](https://github.com/k3s-io/k3s-ansible)
