# Test Environment

Test FluxCD changes locally using kind clusters before deploying to production.

## Overview

The test environment provides a safe, isolated Kubernetes cluster for validating:

- Flux configurations and Kustomizations
- HelmRelease definitions
- Application deployments
- Manifest syntax and structure
- Breaking changes before production

**Key Features:**

- Isolated kind cluster (no impact on production)
- Automated via Task commands
- CI/CD integration (GitHub Actions)
- Mock secrets for testing without real credentials
- Fast iteration cycle

---

## Prerequisites

### Required Tools

- [kind](https://kind.sigs.k8s.io/docs/user/quick-start/#installation)
  \- Kubernetes in Docker
- [kubectl](https://kubernetes.io/docs/tasks/tools/) - Kubernetes CLI
- [kustomize](https://kubectl.docs.kubernetes.io/installation/kustomize/)
  \- Kubernetes manifest customization
- [Docker](https://docs.docker.com/get-docker/) - Container runtime
- [Task](https://taskfile.dev/installation/) - Task runner

Quick install (macOS):

```bash
brew install kind kubectl kustomize go-task/tap/go-task
```

Quick install (Linux):

```bash
# kind
curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.20.0/kind-linux-amd64
chmod +x ./kind
sudo mv ./kind /usr/local/bin/kind

# kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x kubectl
sudo mv kubectl /usr/local/bin/

# kustomize
curl -s "https://raw.githubusercontent.com/kubernetes-sigs/kustomize/master/hack/install_kustomize.sh" | bash
sudo mv kustomize /usr/local/bin/

# task
sh -c "$(curl --location https://taskfile.dev/install.sh)" -- -d -b /usr/local/bin
```

### Docker Requirements

Ensure Docker is running:

```bash
docker ps
```

---

## Quick Start

```bash
# Create test cluster
task test:create

# Install Flux
task test:install-flux

# Apply configurations
task test:apply

# Check status
task test:status

# Clean up
task test:destroy
```

## Available Commands

### Core Operations

| Command | Description |
| ------- | ----------- |
| `task test:create` | Create test cluster |
| `task test:destroy` | Destroy test cluster |
| `task test:reset` | Destroy and recreate |
| `task test:install-flux` | Install Flux controllers |
| `task test:apply` | Apply all configurations |
| `task test:status` | Check cluster status |
| `task test:validate` | Validate manifests |

### Application Testing

```bash
# Test specific app
task test:apply-app APP=cert-manager

# Create mock secrets
task test:mock-secrets
task test:mock-secrets NAMESPACE=home-automation
```

### Debugging

```bash
# View controller logs
task test:logs CONTROLLER=kustomize-controller
task test:logs CONTROLLER=helm-controller

# Open debug shell
task test:shell

# List/clean clusters
task test:list
task test:clean
```

## Common Workflows

### Before Commit

```bash
task test:validate
task test:create
task test:install-flux
task test:apply
task test:status
task test:destroy
```

### Testing Single App

```bash
task test:create
task test:install-flux
task test:apply-app APP=cert-manager
kubectl get pods -n cert-manager -w
```

## Advanced Usage

### Custom Cluster Names

```bash
task test:create TEST_CLUSTER_NAME=my-test
task test:destroy TEST_CLUSTER_NAME=my-test
```

### Multiple Clusters

```bash
task test:create TEST_CLUSTER_NAME=test-a
task test:create TEST_CLUSTER_NAME=test-b
kubectl config use-context kind-test-a
```

## Limitations

Automatically skipped:

- SOPS-encrypted secrets (use `task test:mock-secrets`)
- Deprecated resources
- External dependencies

Production differences:

- Mock secrets vs real encrypted values
- NodePort vs LoadBalancer
- emptyDir vs persistent volumes
- Single node vs HA

## Testable Applications

The following apps can be tested in kind clusters (no external dependencies):

| Application | Namespace | Purpose |
| ----------- | --------- | ------- |
| cert-manager | cert-manager | TLS certificate management |
| external-secrets | external-secrets | Secret synchronization (mock mode) |
| nfs-subdir-external-provisioner | kube-system | Dynamic PV provisioning |
| reflector | kube-system | ConfigMap/Secret mirroring |
| reloader | kube-system | Pod restart on config changes |
| flux-operator | flux-system | Flux cluster operator |
| flux-instance | flux-system | Flux Git sync instance |
| atomic-red-team | attack-simulation | Attack simulation framework |
| ttpforge | attack-simulation | Threat modeling tool |
| system-upgrade-controller | system-upgrade | System upgrades |

**Not Testable** (require external dependencies):

- Apps with 1Password integration (without mocks)
- Apps requiring NFS servers
- Apps requiring external databases
- Apps with hardware dependencies (Unifi, printers, etc.)
- C2 frameworks (Sliver)

---

## Testing Workflow

### 1. Before Every Commit

```bash
# Validate manifests
task test:validate
```

This checks:

- YAML syntax
- Kustomize build success
- Required fields present
- API compatibility

### 2. Testing Major Changes

```bash
# Complete test cycle
task test:create
task test:install-flux
task test:apply
task test:status
task test:destroy
```

### 3. Testing Single Application

```bash
# Create cluster
task test:create

# Install Flux
task test:install-flux

# Test specific app
task test:apply-app APP=cert-manager

# Watch deployment
kubectl get pods -n cert-manager -w

# Check logs if needed
kubectl logs -n cert-manager deploy/cert-manager

# Clean up
task test:destroy
```

### 4. Iterative Development

```bash
# Create cluster once
task test:create
task test:install-flux

# Make changes, then reapply
task test:apply-app APP=my-app

# Repeat as needed...

# Destroy when done
task test:destroy
```

---

## CI/CD Integration

### GitHub Actions Workflow

`.github/workflows/test-manifests.yaml` automatically:

1. **Validates** all Kustomization builds
2. **Creates** kind cluster
3. **Installs** Flux components
4. **Applies** testable apps
5. **Waits** 180s for reconciliation
6. **Verifies** HelmRelease status
7. **Collects** logs on failure
8. **Destroys** cluster

Runs on:

- Every push to main
- Every pull request
- Manual workflow dispatch

View results:

```bash
gh run list --workflow=test-manifests.yaml
gh run view <run-id> --log
```

---

## Troubleshooting

### Cluster Creation Issues

**Problem:** Cluster creation fails

```bash
# Check Docker
docker ps

# Clean up old clusters
kind get clusters
task test:clean

# Retry creation
task test:create
```

**Problem:** Cluster already exists

```bash
# Destroy existing cluster
task test:destroy

# Or use different name
task test:create TEST_CLUSTER_NAME=my-test-2
```

### Flux Installation Issues

**Problem:** Flux pods not starting

```bash
# Check pod status
kubectl get pods -n flux-system

# View pod logs
kubectl logs -n flux-system deploy/source-controller
kubectl logs -n flux-system deploy/kustomize-controller

# Describe failing pod
kubectl describe pod -n flux-system <pod-name>
```

**Problem:** CRDs not found

```bash
# Reinstall Flux
kubectl delete -k kubernetes/bootstrap/flux/
kubectl apply -k kubernetes/bootstrap/flux/
```

### Application Deployment Issues

**Problem:** HelmRelease stuck in "reconciling"

```bash
# Check HelmRelease status
kubectl get hr -A

# Describe HelmRelease
kubectl describe hr <release-name> -n <namespace>

# Check helm-controller logs
task test:logs CONTROLLER=helm-controller

# View all events
kubectl get events -A --sort-by='.lastTimestamp'
```

**Problem:** SOPS decryption errors

```bash
# Expected in test environment - use mock secrets
task test:mock-secrets

# Or skip encrypted apps
task test:apply-app APP=cert-manager  # Non-encrypted apps only
```

**Problem:** Pod CrashLoopBackOff

```bash
# View pod logs
kubectl logs <pod-name> -n <namespace>

# Describe pod for events
kubectl describe pod <pod-name> -n <namespace>

# Check resource constraints
kubectl top pods -n <namespace>
```

### Resource Issues

**Problem:** Pods pending due to resources

```bash
# Check node resources
kubectl describe nodes

# kind clusters have limited resources
# Reduce replicas or test fewer apps simultaneously
```

**Problem:** ImagePullBackOff

```bash
# Check image name/tag
kubectl describe pod <pod-name> -n <namespace>

# kind may need images preloaded for private registries
kind load docker-image <image:tag> --name woe-test
```

### Debugging Commands

```bash
# View all Flux resources
kubectl get gitrepositories,kustomizations,helmreleases -A

# Check Flux controller logs
task test:logs CONTROLLER=kustomize-controller
task test:logs CONTROLLER=helm-controller
task test:logs CONTROLLER=source-controller

# Open debug shell in cluster
task test:shell

# Export logs from all Flux controllers
kubectl logs -n flux-system -l app.kubernetes.io/part-of=flux --tail=100

# Check specific Kustomization
kubectl describe kustomization <name> -n flux-system

# Force reconciliation
kubectl annotate kustomization <name> -n flux-system \
  reconcile.fluxcd.io/requestedAt="$(date +%s)"
```

### Clean Up

```bash
# List all test clusters
task test:list

# Destroy specific cluster
task test:destroy TEST_CLUSTER_NAME=my-test

# Clean all test clusters
task test:clean

# Reset and recreate
task test:reset
```

---

## Performance Tips

### Speed Up Testing

1. **Keep cluster running** between tests:

   ```bash
   task test:create
   task test:install-flux
   # Make changes, then just reapply
   task test:apply-app APP=my-app
   ```

2. **Test specific apps** instead of all:

   ```bash
   task test:apply-app APP=cert-manager
   ```

3. **Validate before creating cluster**:

   ```bash
   task test:validate  # Fast, no cluster needed
   ```

4. **Use multiple clusters** for parallel testing:

   ```bash
   task test:create TEST_CLUSTER_NAME=test-a
   task test:create TEST_CLUSTER_NAME=test-b
   kubectl config use-context kind-test-a
   ```

### Resource Management

- kind clusters use ~2GB RAM minimum
- Each app adds ~100-500MB depending on size
- Test fewer apps simultaneously if resources limited
- Close other Docker containers to free resources

---

## Best Practices

1. **Always validate** before cluster creation:

   ```bash
   task test:validate
   ```

2. **Test changes** before committing:

   ```bash
   task test:create && task test:install-flux && task test:apply
   ```

3. **Clean up** after testing:

   ```bash
   task test:destroy
   ```

4. **Use descriptive names** for multiple clusters:

   ```bash
   task test:create TEST_CLUSTER_NAME=feature-xyz
   ```

5. **Check CI/CD results** before merging:

   ```bash
   gh run list --workflow=test-manifests.yaml
   ```

6. **Document test dependencies** in app manifests

7. **Use mock secrets** for testing encrypted apps:

   ```bash
   task test:mock-secrets NAMESPACE=my-namespace
   ```

---

## Testing Checklist

Before merging a PR:

- [ ] `task test:validate` passes
- [ ] Local test cluster deployment succeeds
- [ ] GitHub Actions test workflow passes
- [ ] No new SOPS encryption errors
- [ ] HelmRelease reconciles successfully
- [ ] Pods reach Running state
- [ ] No resource limit issues
- [ ] Documentation updated if needed

---

## Resources

- [Main README](../README.md)
- [Developer Guide](dev.md)
- [Bootstrap Instructions](../kubernetes/bootstrap/README.md)
- [Kind Documentation](https://kind.sigs.k8s.io/)
- [Flux Documentation](https://fluxcd.io/flux/)
- [Kustomize Documentation](https://kubectl.docs.kubernetes.io/references/kustomize/)
- [Task Documentation](https://taskfile.dev/)
