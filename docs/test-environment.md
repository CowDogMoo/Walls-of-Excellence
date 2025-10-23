# Test Environment

Test FluxCD changes locally using kind clusters before deploying to production.

## Prerequisites

- [kind](https://kind.sigs.k8s.io/docs/user/quick-start/#installation)
- [kubectl](https://kubernetes.io/docs/tasks/tools/)
- [Docker](https://docs.docker.com/get-docker/)

Quick install (macOS):

```bash
brew install kind kubectl
```

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
|---------|-------------|
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

## Troubleshooting

```bash
# Cluster creation fails
docker ps
task test:destroy && task test:create

# View logs
task test:logs CONTROLLER=kustomize-controller

# Check resources
kubectl get pods -A
kubectl get events -A --sort-by='.lastTimestamp'
kubectl describe kustomization <name> -n flux-system
```

## Resources

- [Main README](../README.md)
- [Developer Guide](dev.md)
- [Kind Documentation](https://kind.sigs.k8s.io/)
- [Flux Documentation](https://fluxcd.io/flux/)
