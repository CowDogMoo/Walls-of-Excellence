# Weave GitOps

Weave GitOps provides a web UI for managing Flux-based GitOps workflows.

## Authentication

Weave GitOps is configured with dual authentication methods:

### 1. Admin User (Built-in)

- Username: `admin`
- Password: Stored in `weave-gitops-secret` (synced from 1Password)

### 2. OIDC/OAuth2 via Authentik

- Issuer: `https://auth.techvomit.xyz/application/o/weave-gitops/`
- Provider: Authentik OAuth2
- Group: "Weave GitOps Admins" (must be member to access)

## Setup

### Prerequisites

1. Authentik OAuth2 provider configured
   (see `kubernetes/apps/identity/README.md`)
2. User added to "Weave GitOps Admins" group in Authentik
3. OIDC user added to Kubernetes RBAC (see below)

### Adding OIDC Users

Edit the following file:
`kubernetes/apps/flux-system/weave-gitops/app/oidc-user-clusterrolebinding.yaml`

```yaml
subjects:
  - apiGroup: rbac.authorization.k8s.io
    kind: User
    name: your-email@example.com  # Add your OIDC user email
```

Multiple users can be added:

```yaml
subjects:
  - apiGroup: rbac.authorization.k8s.io
    kind: User
    name: user1@example.com
  - apiGroup: rbac.authorization.k8s.io
    kind: User
    name: user2@example.com
```

Commit and push changes - Flux will apply automatically.

## Access

- URL: https://weave.techvomit.xyz
- Admin login: Use username/password
- OIDC login: Click "Login with OIDC"

## Troubleshooting

### No Data After OIDC Login

**Symptom**: Successfully authenticated but dashboard shows no
applications or resources.

**Cause**: OIDC user lacks Kubernetes RBAC permissions.

**Solution**:

1. Verify user is in `oidc-user-clusterrolebinding.yaml`
2. Check Kubernetes RBAC:

   ```bash
   kubectl auth can-i get helmreleases --as=your-email@example.com \
     -n flux-system
   ```

3. Should return `yes`

### RESTMapper Error

**Error**: `could not create RESTMapper from config: unknown`

**Cause**: ServiceAccount lacks API discovery permissions.

**Solution**: Already fixed via Kustomize patch in
`clusterrole-patch.yaml` which adds nonResourceURLs permissions.

### Impersonation Error

**Error**: `cannot impersonate resource "users" in API group ""`

**Cause**: weave-gitops ServiceAccount can't impersonate OIDC users.

**Solution**: Already fixed - `impersonationResourceNames: []` allows
impersonating any user.

## Configuration Files

- `helmrelease.yaml` - Main Weave GitOps configuration
- `oidc-user-clusterrolebinding.yaml` - RBAC for OIDC users
- `clusterrole-patch.yaml` - API discovery permissions patch
- `externalsecret.yaml` - Admin password from 1Password

## RBAC Permissions

OIDC users get permissions via the `wego-admin-cluster-role` which
includes:

- Read access to all resources (`get`, `list`, `watch` on `*.*`)
- Patch access to Flux resources:
  - HelmReleases
  - Kustomizations
  - GitRepositories
  - HelmRepositories
  - OCIRepositories
  - Buckets
  - HelmCharts

## Security Notes

- Admin password rotates via 1Password
- OIDC users require both:
  1. Authentik group membership ("Weave GitOps Admins")
  2. Kubernetes RBAC (ClusterRoleBinding)
- User impersonation is unrestricted but users still need RBAC
  permissions
