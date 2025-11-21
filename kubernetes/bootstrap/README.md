# Bootstrap Instructions

Bootstrap configuration for the Kubernetes cluster using Task + Helmfile.

## Overview

The bootstrap process prepares a fresh k3s cluster for GitOps management by:

1. Creating required namespaces
2. Injecting secrets from 1Password
3. Installing CRDs from core charts
4. Deploying foundational applications
5. Setting up Flux for ongoing reconciliation

**Bootstrap Apps** (deployed via Helmfile):

- **cert-manager** - TLS certificate management
- **external-secrets** - 1Password secret synchronization
- **flux-operator** - Flux cluster operator
- **flux-instance** - Flux Git synchronization

After bootstrap, Flux takes over and manages all applications from Git.

---

## Prerequisites

### Required Tools

- **kubectl** - Kubernetes CLI
- **task** - Task runner (go-task)
- **helmfile** - Helm release orchestrator
- **helm** - Kubernetes package manager
- **kustomize** - Manifest customization
- **yq** - YAML processor
- **op** - 1Password CLI (authenticated)

Install via Homebrew:

```bash
brew install kubectl go-task/tap/go-task helmfile helm kustomize yq
brew install --cask 1password-cli
```

### Cluster Prerequisites

- k3s cluster provisioned via Ansible
- Nodes in Ready state
- SSH access to nodes
- kubectl configured with cluster access

Verify:

```bash
kubectl get nodes
```

---

## Directory Structure

```text
bootstrap/
├── README.md                          # This file
├── flux/                              # Flux components
│   ├── gotk-components.yaml          # Flux CRDs and controllers
│   ├── gotk-sync.yaml                # GitRepository and Kustomization
│   └── age-key.secret.sops.yaml      # SOPS age encryption key
├── helmfile.d/                        # Helmfile configurations
│   ├── 00-crds.yaml                  # CRD extraction from charts
│   ├── 01-apps.yaml                  # Core bootstrap applications
│   └── templates/
│       └── values.yaml.gotmpl        # Values template (reads from apps/)
└── resources.yaml.j2                 # Bootstrap resources with 1Password refs
```

---

## Bootstrap Process

### Complete Bootstrap (Recommended)

Run the entire bootstrap sequence:

```bash
task bootstrap
```

This executes all stages in order:

1. Wait for nodes to be ready
2. Create namespaces
3. Apply bootstrap resources (secrets)
4. Install CRDs
5. Deploy core applications

### Individual Stages

Run bootstrap stages individually for troubleshooting:

```bash
# 1. Wait for all nodes to be ready
task bootstrap:wait

# 2. Create Kubernetes namespaces from app manifests
task bootstrap:namespaces

# 3. Apply secrets via 1Password injection
task bootstrap:resources

# 4. Install CRDs from Helm charts
task bootstrap:crds

# 5. Deploy core applications via Helmfile
task bootstrap:apps
```

### Post-Bootstrap Verification

```bash
# Check all pods are running
kubectl get pods -A

# Verify Flux controllers
kubectl get pods -n flux-system

# Check HelmReleases
kubectl get hr -A

# View Flux Kustomizations
flux get kustomizations -A
```

---

## 1Password Setup

### Required Secrets

Store the following secrets in 1Password vault `kubernetes`:

| Item | Field | Description |
| ---- | ----- | ----------- |
| `1password` | `OP_CREDENTIALS_JSON` | 1Password Connect credentials |
| `1password` | `OP_CONNECT_TOKEN` | 1Password Connect API token |
| `sops` | `SOPS_PRIVATE_KEY` | age private key for SOPS encryption |

### Authentication

Authenticate with 1Password CLI before bootstrap:

```bash
# Sign in
op signin

# Verify authentication
op whoami

# Test secret retrieval
op read "op://kubernetes/sops/SOPS_PRIVATE_KEY"
```

### Troubleshooting 1Password

**Problem:** `op` command not found

```bash
brew install --cask 1password-cli
```

**Problem:** Not signed in

```bash
op signin
```

**Problem:** Cannot find vault or item

```bash
# List vaults
op vault list

# List items in vault
op item list --vault kubernetes
```

---

## SOPS Setup (First-Time Only)

For new clusters, set up SOPS encryption:

### 1. Generate age Key

```bash
# Generate new age key pair
age-keygen -o keys.txt

# View the key
cat keys.txt
```

Output:

```text
# created: 2024-01-01T00:00:00Z
# public key: age1xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
AGE-SECRET-KEY-1XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

### 2. Store Private Key in 1Password

1. Open 1Password
2. Create/edit item in `kubernetes` vault:
   - Name: `sops`
   - Field: `SOPS_PRIVATE_KEY`
   - Value: The `AGE-SECRET-KEY-1...` line

### 3. Update .sops.yaml

Add the public key to `.sops.yaml` in the repository root:

```yaml
creation_rules:
  - path_regex: kubernetes/.*\.sops\.yaml$
    age: age1xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 4. Create Flux age Secret

Create `kubernetes/bootstrap/flux/age-key.secret.sops.yaml`:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: sops-age
  namespace: flux-system
stringData:
  age.agekey: |
    # created: 2024-01-01T00:00:00Z
    # public key: age1xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    AGE-SECRET-KEY-1XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

Encrypt it:

```bash
sops --encrypt --in-place kubernetes/bootstrap/flux/age-key.secret.sops.yaml
```

### 5. Commit and Push

```bash
git add .sops.yaml kubernetes/bootstrap/flux/age-key.secret.sops.yaml
git commit -m "feat: add SOPS age encryption key"
git push
```

---

## Helmfile Configuration

### CRD Extraction (00-crds.yaml)

Extracts CRDs from charts before application installation:

```yaml
repositories:
  - name: cert-manager
    url: https://charts.jetstack.io
  - name: external-secrets
    url: https://charts.external-secrets.io

releases:
  - name: cert-manager
    chart: cert-manager/cert-manager
    version: 1.19.1
    # Extract CRDs only
```

### Core Apps (01-apps.yaml)

Deploys foundational applications:

```yaml
releases:
  - name: cert-manager
    namespace: cert-manager
    chart: cert-manager/cert-manager
    version: 1.19.1
    values:
      - installCRDs: false  # Already installed

  - name: external-secrets
    namespace: external-secrets
    chart: external-secrets/external-secrets
    version: 1.0.0
```

### Values Templates

Helmfile templates read values from `kubernetes/apps/*/app/helmrelease.yaml`
to maintain consistency with Flux-managed deployments.

---

## Bootstrap Resources

### resources.yaml.j2

Template file with 1Password references:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: onepassword-credentials
  namespace: external-secrets
stringData:
  credentials.json: "op://kubernetes/1password/OP_CREDENTIALS_JSON"
  token: "op://kubernetes/1password/OP_CONNECT_TOKEN"
---
apiVersion: v1
kind: Secret
metadata:
  name: sops-age
  namespace: flux-system
stringData:
  age.agekey: "op://kubernetes/sops/SOPS_PRIVATE_KEY"
```

These are injected during bootstrap via:

```bash
op inject -i kubernetes/bootstrap/resources.yaml.j2 | kubectl apply -f -
```

---

## Flux Installation

### Flux Components

Located in `kubernetes/bootstrap/flux/`:

- **gotk-components.yaml** - Flux controllers and CRDs
- **gotk-sync.yaml** - GitRepository and Kustomization for cluster sync

### Install Flux

Flux is installed as part of the bootstrap apps:

```bash
task bootstrap:apps
```

Or manually:

```bash
kubectl apply -k kubernetes/bootstrap/flux/
```

### Verify Flux

```bash
# Check Flux pods
kubectl get pods -n flux-system

# Check Flux version
flux version

# Check Git sync
flux get sources git -A

# Check Kustomizations
flux get kustomizations -A
```

---

## Post-Bootstrap

After bootstrap completes, Flux manages all remaining applications from Git.

### Verify Flux Reconciliation

```bash
# Sync Flux system
flux reconcile ks flux-system --with-source

# Sync cluster apps
flux reconcile ks cluster-apps --with-source -n flux-system

# Watch Flux
flux get all -A
```

### Check Application Status

```bash
# View all HelmReleases
kubectl get hr -A

# Check specific app
kubectl get hr -n cert-manager cert-manager

# View events
kubectl get events -A --sort-by='.lastTimestamp'
```

### View Logs

```bash
# Flux controller logs
kubectl logs -n flux-system deploy/kustomize-controller -f
kubectl logs -n flux-system deploy/helm-controller -f
kubectl logs -n flux-system deploy/source-controller -f

# Application logs
kubectl logs -n cert-manager deploy/cert-manager
```

---

## Troubleshooting

### Bootstrap Failures

**Problem:** Nodes not ready

```bash
# Check node status
kubectl get nodes

# Wait for nodes
task bootstrap:wait

# Check k3s service
ssh k8s1 'sudo systemctl status k3s'
```

**Problem:** 1Password authentication fails

```bash
# Re-authenticate
op signin

# Verify authentication
op whoami

# Test secret access
op read "op://kubernetes/sops/SOPS_PRIVATE_KEY"
```

**Problem:** CRD installation fails

```bash
# Check CRD template generation
helmfile -f kubernetes/bootstrap/helmfile.d/00-crds.yaml template -q

# Manually apply CRDs
task bootstrap:crds
```

**Problem:** Helm release fails

```bash
# Check Helm releases
helm list -A

# View Helm release details
helm get values <release-name> -n <namespace>
helm get manifest <release-name> -n <namespace>

# Retry apps deployment
task bootstrap:apps
```

### Flux Issues

**Problem:** Flux controllers not starting

```bash
# Check pod status
kubectl get pods -n flux-system

# View pod logs
kubectl logs -n flux-system deploy/source-controller
kubectl logs -n flux-system deploy/kustomize-controller

# Reinstall Flux
kubectl delete -k kubernetes/bootstrap/flux/
kubectl apply -k kubernetes/bootstrap/flux/
```

**Problem:** Git sync failing

```bash
# Check GitRepository
flux get sources git -A

# Describe GitRepository
kubectl describe gitrepository flux-system -n flux-system

# Force reconcile
flux reconcile source git flux-system
```

**Problem:** SOPS decryption errors

```bash
# Verify age secret exists
kubectl get secret sops-age -n flux-system

# Check age key format
kubectl get secret sops-age -n flux-system -o yaml

# Recreate secret
task bootstrap:resources
```

### General Debugging

```bash
# Check all resources
kubectl get all -A

# View recent events
kubectl get events -A --sort-by='.lastTimestamp' | tail -20

# Check resource usage
kubectl top nodes
kubectl top pods -A

# Describe failing resources
kubectl describe <resource-type> <resource-name> -n <namespace>
```

---

## Maintenance

### Updating Chart Versions

Chart versions are in `helmfile.d/*.yaml`. Update and resync:

```bash
# Edit helmfile
vim kubernetes/bootstrap/helmfile.d/01-apps.yaml

# Sync changes
helmfile -f kubernetes/bootstrap/helmfile.d/01-apps.yaml sync
```

### Updating Flux

```bash
# Check current version
flux version

# Export new version
flux install --export > kubernetes/bootstrap/flux/gotk-components.yaml

# Apply update
kubectl apply -k kubernetes/bootstrap/flux/

# Verify
flux version
```

### Keeping Values Synchronized

Bootstrap helmfile values should match
`kubernetes/apps/*/app/helmrelease.yaml` definitions for consistency.

---

## Complete Bootstrap Workflow

For a new cluster from scratch:

```bash
# 1. Provision k3s cluster
task provision

# 2. Verify cluster access
kubectl get nodes

# 3. Authenticate with 1Password
op signin

# 4. Run bootstrap
task bootstrap

# 5. Verify bootstrap
kubectl get pods -A
helm list -A

# 6. Check Flux
flux get kustomizations -A
flux get helmreleases -A

# 7. Sync cluster apps
flux reconcile ks cluster-apps --with-source -n flux-system

# 8. Monitor deployment
kubectl get pods -A -w
```

---

## Resources

- [Main README](../../README.md)
- [Developer Guide](../../docs/dev.md)
- [Test Environment](../../docs/test-environment.md)
- [Flux Documentation](https://fluxcd.io/flux/)
- [Helmfile Documentation](https://helmfile.readthedocs.io/)
- [cert-manager Documentation](https://cert-manager.io/)
- [external-secrets Documentation](https://external-secrets.io/)
- [1Password CLI Documentation](https://developer.1password.com/docs/cli/)
- [SOPS Documentation](https://github.com/getsops/sops)
