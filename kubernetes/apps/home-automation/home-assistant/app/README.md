# Home Assistant

A Kubernetes deployment of Home Assistant with automatic git-sync for
configuration management.

## Overview

This deployment runs Home Assistant Core with automatic configuration
synchronization from a GitHub repository using GitHub App authentication. The
configuration files are stored on NFS for persistence, and a sidecar container
automatically pulls changes from the git repository every 60 seconds.

## Features

- **Automatic Git Sync**: Configuration syncs from GitHub every 60 seconds
- **GitHub App Authentication**: Secure, auditable authentication using GitHub App
- **Configurable Branch**: Easy branch switching for testing configurations
- **NFS Persistence**: Configuration stored on NFS for multi-pod access
- **OIDC Integration**: Authentik integration for single sign-on
- **Custom Components**: Automatic installation of custom components (OIDC auth)
- **Secure Secrets**: Uses 1Password via External Secrets for credentials

## Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│  Home Assistant Pod                                          │
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   app        │    │  git-pull    │    │  ts-config   │  │
│  │  (HA Core)   │◄───│  (sidecar)   │    │  monitor     │  │
│  └──────┬───────┘    └──────┬───────┘    └──────────────┘  │
│         │                   │                               │
│         │                   │                               │
└─────────┼───────────────────┼───────────────────────────────┘
          │                   │
          ▼                   ▼
    ┌─────────────┐     ┌─────────────┐
    │  NFS        │     │  GitHub     │
    │  /config    │     │  Repository │
    └─────────────┘     └─────────────┘
          │                   │
          ▼                   │
    ┌─────────────┐           │
    │  External   │◄──────────┘
    │  Secret     │
    │ (1Password) │
    └─────────────┘
```

## Configuration

### 1Password Setup

The deployment expects these 1Password items:

#### `authentik-secrets`

- **HOMEASSISTANT_CLIENT_SECRET**: Authentik OIDC client secret

#### `CowDogMoo Github App`

- **ACTIONS_RUNNER_APP_ID**: GitHub App ID
- **ACTIONS_RUNNER_INSTALLATION_ID**: GitHub App installation ID

#### `cowdogmoo-renovate-bot-private-key`

- **private_key**: GitHub App private key (PEM format)

### Git Sync Configuration

Configured in `helmrelease.yaml`:

- `GIT_SYNC_BRANCH`: Branch to sync (default: `main`)
- Repository: `https://github.com/CowDogMoo/homeassistant`
- Sync interval: 60 seconds

### NFS Storage

The `/config` directory is mounted from NFS:

- Server: `192.168.20.210`
- Path: `/volume1/k8s/home-assistant`

## Deployment

### Prerequisites

1. 1Password Connect installed in cluster
2. `onepassword-connect` ClusterSecretStore configured
3. External Secrets Operator running
4. GitHub App with access to the homeassistant repository
5. NFS server accessible from the cluster

### Installation

1. Ensure all 1Password items exist with correct fields

2. Deploy via Flux (automatic):

   ```bash
   flux reconcile ks cluster-apps --with-source -n flux-system
   ```

3. Or manually apply:

   ```bash
   kubectl apply -f kubernetes/apps/home-automation/home-assistant/app/
   ```

## Operations

### View Pod Status

```bash
kubectl get pods -n home-automation -l app.kubernetes.io/name=home-assistant
```

### View Logs

```bash
# Home Assistant logs
kubectl logs -n home-automation -l app.kubernetes.io/name=home-assistant -c app

# Git sync logs
kubectl logs -n home-automation -l app.kubernetes.io/name=home-assistant -c git-pull -f

# Config monitor logs
kubectl logs -n home-automation -l app.kubernetes.io/name=home-assistant -c ts-config-monitor
```

### Testing Development Branches

To test configuration changes from a development branch:

1. Edit `helmrelease.yaml` and change the branch:

   ```yaml
   env:
     - name: GIT_SYNC_BRANCH
       value: "dev-branch"  # Change from "main"
   ```

2. Apply the change:

   ```bash
   kubectl apply -f kubernetes/apps/home-automation/home-assistant/app/helmrelease.yaml
   ```

3. The pod will restart and sync from the new branch

4. To return to main, change back to `value: "main"` and reapply

### Manual Configuration Access

```bash
# Exec into the pod
kubectl exec -it -n home-automation <pod-name> -c app -- sh

# View configuration
cd /config
ls -la

# Check git status
git status

# View current branch
git branch --show-current
```

**Note**: Manual git operations will be overridden by the git-pull sidecar
within 60 seconds. Use the `GIT_SYNC_BRANCH` environment variable to control
which branch is synced.

### Verify Git Sync is Working

```bash
# Check git-pull logs for sync messages
kubectl logs -n home-automation -l app.kubernetes.io/name=home-assistant -c git-pull --tail=20

# Expected output:
# Configured to sync branch: main
# Fetching latest changes from repository
# Successfully pulled latest changes from main
```

### Troubleshooting

#### Git sync not pulling changes

1. Check the git-pull container logs:

   ```bash
   kubectl logs -n home-automation <pod-name> -c git-pull
   ```

2. Verify GitHub App permissions:
   - App must have **Contents: Read** permission
   - App must be installed on the `CowDogMoo/homeassistant` repository

3. Verify External Secret is syncing:

   ```bash
   kubectl get externalsecrets -n home-automation
   kubectl describe externalsecret home-assistant-secrets -n home-automation
   ```

#### Pod failing to start

1. Check init container logs:

   ```bash
   kubectl logs -n home-automation <pod-name> -c install-oidc-component
   kubectl logs -n home-automation <pod-name> -c setup-ts
   kubectl logs -n home-automation <pod-name> -c setup-oidc
   ```

2. Verify NFS mount is accessible:

   ```bash
   kubectl describe pod <pod-name> -n home-automation | grep -A 5 "Volumes:"
   ```

#### Configuration changes not applying

1. Verify files are being pulled:

   ```bash
   kubectl exec -n home-automation <pod-name> -c app -- ls -la /config
   ```

2. Check Home Assistant logs for configuration errors:

   ```bash
   kubectl logs -n home-automation <pod-name> -c app | grep -i error
   ```

3. Restart Home Assistant to reload configuration:

   ```bash
   kubectl delete pod -n home-automation <pod-name>
   ```

### Adjusting Sync Frequency

Edit the sleep duration in `helmrelease.yaml`:

```yaml
# Every 60 seconds (default)
sleep 60

# Every 5 minutes
sleep 300

# Every 30 seconds
sleep 30
```

### GitHub App Token Refresh

The git-pull sidecar generates a fresh GitHub App token for each sync cycle.
Tokens are valid for 1 hour but are regenerated every 60 seconds, ensuring
continuous access without manual intervention.

## Configuration Repository

Your Home Assistant configuration lives at:

- **Repository**: https://github.com/CowDogMoo/homeassistant
- **Branch**: Configured via `GIT_SYNC_BRANCH` (default: `main`)

### Idiomatic Workflow

1. **Make changes** to configuration files in your git repository
2. **Commit and push** to GitHub
3. **Wait 60 seconds** for automatic sync to Kubernetes
4. **Verify changes** in Home Assistant

For testing:

1. **Create a branch** for your changes
2. **Update `GIT_SYNC_BRANCH`** to your test branch
3. **Test thoroughly** in Kubernetes
4. **Merge to main** when ready
5. **Switch back** to `GIT_SYNC_BRANCH: main`

## Resources

- [Home Assistant Documentation](https://www.home-assistant.io/docs/)
- [Home Assistant Docker Image](https://github.com/home-assistant/docker)
- [GitHub Apps Documentation](https://docs.github.com/en/apps)
- [External Secrets Operator](https://external-secrets.io/)
- [1Password Connect](https://developer.1password.com/docs/connect/)
- [bjw-s app-template Helm Chart](https://github.com/bjw-s-labs/helm-charts/tree/main/charts/other/app-template)
