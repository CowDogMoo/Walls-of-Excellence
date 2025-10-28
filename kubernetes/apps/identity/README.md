# Authentik SSO Configuration

This directory contains the configuration for Authentik, an open-source
Identity Provider (IdP) that provides SSO, OAuth2, SAML, and forward
authentication for applications in the cluster.

## Overview

Authentik is configured to provide authentication for:

- **Weave GitOps** - OIDC/OAuth2 authentication
- **Apache Guacamole** - Forward auth with header authentication
- **Traefik Dashboard** - Forward auth
- **Grafana** - OAuth2 authentication

## Architecture

```text
┌─────────────────┐
│   User Browser  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Traefik Proxy  │ (Forward Auth Middleware)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    Authentik    │
│  Embedded       │
│  Outpost        │
└────────┬────────┘
         │
    ┌────┴─────┬─────────────┬──────────────┐
    ▼          ▼             ▼              ▼
┌─────────┐ ┌──────────┐ ┌────────────┐ ┌──────────┐
│ Grafana │ │ Traefik  │ │ Guacamole  │ │  Weave   │
│ (OAuth) │ │ (Forward)│ │  (Forward) │ │  GitOps  │
│         │ │          │ │            │ │  (OIDC)  │
└─────────┘ └──────────┘ └────────────┘ └──────────┘
```

## Blueprint Configuration

Authentik uses "blueprints" to declaratively configure providers,
applications, groups, and policies. The main blueprint is located at:

- `kubernetes/apps/identity/authentik/app/authentik-oauth-blueprint.yaml`

### Blueprint Structure

```yaml
context:
  # Client secrets loaded from environment variables
  grafana_client_secret: !Env GRAFANA_CLIENT_SECRET
  weave_gitops_client_secret: !Env WEAVE_GITOPS_CLIENT_SECRET
  # ... etc

entries:
  # Groups for access control
  - model: authentik_core.group
    id: weave-gitops-admins
    # ...

  # OAuth2/Proxy Providers
  - model: authentik_providers_oauth2.oauth2provider
    id: weave-gitops-provider
    # ...

  # Applications
  - model: authentik_core.application
    id: weave-gitops-app
    # ...

  # Access Policies
  - model: authentik_policies_expression.expressionpolicy
    id: weave-gitops-admin-policy
    # ...

  # Policy Bindings
  - model: authentik_policies.policybinding
    # ...

  # Outpost Configuration
  - model: authentik_outposts.outpost
    identifiers:
      name: authentik Embedded Outpost
    attrs:
      providers:
        - !KeyOf traefik-provider
        - !KeyOf guacamole-provider
```

## Manual Configuration Steps

After the Flux deployment, the following manual steps are required in
the Authentik UI:

### 1. Access Authentik Admin Interface

Navigate to: https://auth.techvomit.xyz/if/admin/

### 2. Create User Groups

Go to **Directory** → **Groups** and verify/create the following
groups:

- **Grafana Admins** - Full admin access to Grafana
- **Grafana Editors** - Editor access to Grafana
- **Traefik Admins** - Access to Traefik dashboard
- **Weave GitOps Admins** - Access to Weave GitOps dashboard
- **Guacamole Users** - Access to Guacamole remote desktop

### 3. Add Users to Groups

For each user that needs access:

1. Go to **Directory** → **Users**
2. Select the user (e.g., your email address)
3. Click the **Groups** tab
4. Add the user to appropriate groups:
   - Add yourself to **Weave GitOps Admins** for GitOps dashboard
     access
   - Add yourself to **Guacamole Users** for remote desktop access
   - Add yourself to **Traefik Admins** for Traefik dashboard access
   - Add yourself to **Grafana Admins** for full Grafana access

### 4. Verify Blueprint Application

The blueprint should be automatically applied by the Authentik worker.
To manually trigger:

```bash
kubectl exec -n identity deploy/authentik-worker -- \
  ak apply_blueprint \
  /blueprints/mounted/cm-authentik-oauth-blueprint/oauth-providers.yaml
```

### 5. Verify Providers

Go to **Applications** → **Providers** and verify:

- ✅ **Grafana** (OAuth2 Provider)
- ✅ **Weave GitOps** (OAuth2 Provider)
- ✅ **Traefik Dashboard** (Proxy Provider)
- ✅ **Guacamole** (Proxy Provider)

### 6. Verify Applications

Go to **Applications** → **Applications** and verify:

- ✅ **Grafana** - OAuth2 app with launch URL
- ✅ **Weave GitOps** - OAuth2 app with launch URL
- ✅ **Traefik Dashboard** - Proxy app with launch URL
- ✅ **Guacamole** - Proxy app with launch URL

### 7. Verify Policies

Go to **Applications** → **Applications** → Select each app →
**Policy / Group / User Bindings** tab:

- **Traefik Dashboard**: Bound to `traefik-admin-policy` (requires
  Traefik Admins group)
- **Weave GitOps**: Bound to `weave-gitops-admin-policy` (requires
  Weave GitOps Admins group)
- **Guacamole**: Bound to `guacamole-user-policy` (requires
  Guacamole Users group)

### 8. Verify Embedded Outpost

Go to **Applications** → **Outposts** →
**authentik Embedded Outpost**:

Verify providers are assigned:

- ✅ Traefik Dashboard
- ✅ Guacamole

## Service-Specific Configuration

### Weave GitOps (OIDC)

Weave GitOps uses native OIDC authentication.

**Key Configuration**:

- Issuer URL: `https://auth.techvomit.xyz/application/o/weave-gitops/`
  (trailing slash required!)
- Client ID: `weave-gitops`
- Redirect URL: `https://weave.techvomit.xyz/oauth2/callback`
- Signing Algorithm: RS256 with "authentik Internal JWT Certificate"

**Additional Kubernetes RBAC**:
Users authenticated via OIDC need Kubernetes RBAC permissions. A
ClusterRoleBinding is created to grant OIDC users access to Flux
resources:

```yaml
# File path:
# kubernetes/apps/flux-system/weave-gitops/app/
#   oidc-user-clusterrolebinding.yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: weave-gitops-oidc-users
roleRef:
  kind: ClusterRole
  name: wego-admin-cluster-role
subjects:
  - kind: User
    name: jayson.e.grace@gmail.com  # Replace with your email
```

**Testing**:

1. Navigate to https://weave.techvomit.xyz
2. Click "Login with OIDC"
3. Authenticate with Authentik
4. Should land on Weave GitOps dashboard with Flux resources
   visible

### Guacamole (Forward Auth + Header Auth)

Guacamole uses Traefik forward auth combined with header-based
authentication.

**Forward Auth Flow**:

1. User requests https://guacamole.techvomit.xyz
2. Traefik forwards auth request to Authentik outpost
3. Authentik validates user and group membership
4. If authorized, Authentik returns headers including
   `X-authentik-username`
5. Traefik forwards request to Guacamole with headers
6. Guacamole reads `X-authentik-username` header and auto-logs in
   user

**Header Authentication Configuration**:

```properties
# /config/guacamole/guacamole.properties
http-auth-header: X-authentik-username
```

This is automatically configured via a postStart lifecycle hook in the
deployment.

**Testing**:

1. Navigate to https://guacamole.techvomit.xyz
2. Automatically redirected to Authentik
3. After authentication, automatically logged into Guacamole (no
   login form)

### Traefik Dashboard (Forward Auth)

Similar to Guacamole, uses forward authentication.

**Testing**:

1. Navigate to https://traefik.techvomit.xyz
2. Authenticate with Authentik
3. Access Traefik dashboard

## Secrets Management

Client secrets are stored in 1Password and synced via External Secrets
Operator:

```yaml
# kubernetes/apps/identity/authentik/app/externalsecret.yaml
spec:
  data:
    - secretKey: GRAFANA_CLIENT_SECRET
      remoteRef:
        key: authentik
        property: grafana-client-secret
    - secretKey: WEAVE_GITOPS_CLIENT_SECRET
      remoteRef:
        key: authentik
        property: weave-gitops-client-secret
    # ... etc
```

### Adding New Client Secrets

1. Generate secret: `openssl rand -base64 32`
2. Add to 1Password vault under `authentik` item
3. Add to `externalsecret.yaml`
4. Add to `authentik-oauth-blueprint.yaml` context
5. Add valuesFrom to `helmrelease.yaml` (if needed)

## Troubleshooting

### Blueprint Not Applied

Check worker logs:

```bash
kubectl logs -n identity deploy/authentik-worker --tail=100
```

Manually apply blueprint:

```bash
kubectl exec -n identity deploy/authentik-worker -- \
  ak apply_blueprint \
  /blueprints/mounted/cm-authentik-oauth-blueprint/oauth-providers.yaml
```

### Weave GitOps: "No Data" After Login

**Issue**: User authenticated but dashboard shows no data.

**Cause**: OIDC user lacks Kubernetes RBAC permissions.

**Fix**: Add user to `oidc-user-clusterrolebinding.yaml`:

```yaml
subjects:
  - kind: User
    name: your-email@example.com  # Add your email
```

### Guacamole: Still Shows Login Form

**Issue**: Guacamole shows login form after Authentik auth.

**Causes**:

1. Header auth not configured in guacamole.properties
2. Not in "Guacamole Users" group

**Fix**:

```bash
# Verify header auth is configured
kubectl exec -n guacamole deploy/guacamole -- \
  cat /config/guacamole/guacamole.properties | grep http-auth-header

# Should show: http-auth-header: X-authentik-username
```

### OIDC Token Signing Errors

**Error**: `oidc: id token signed with unsupported algorithm, expected
["RS256"] got "HS256"`

**Fix**: Ensure OAuth2 provider uses `signing_key` pointing to
"authentik Internal JWT Certificate":

```yaml
- model: authentik_providers_oauth2.oauth2provider
  attrs:
    signing_key: !Find [
      authentik_crypto.certificatekeypair,
      [name, authentik Internal JWT Certificate]
    ]
```

## Security Considerations

### Forward Auth Header Sanitization

**CRITICAL**: When using forward auth with header authentication (like
Guacamole), ensure the `X-authentik-*` headers are stripped from
untrusted requests. Traefik's forward auth middleware handles this
automatically - the headers are ONLY added after successful Authentik
authentication.

**Never** expose services directly without the middleware, as users
could manually add headers to bypass authentication.

### Certificate Types

Authentik has two certificate types:

- **authentik Internal JWT Certificate** - For RS256 JWT signing (OAuth2/OIDC)
- **authentik Self-signed Certificate** - For TLS

Use the correct certificate for each purpose.

### Group-Based Access Control

All applications use group-based policies. Users must be in the
appropriate group to access each service:

- No group membership = No access (401/403)
- Wrong group = No access
- Correct group = Authenticated and authorized

## References

- [Authentik Documentation](https://docs.goauthentik.io/)
- [Authentik Blueprints]
  (https://docs.goauthentik.io/docs/terminology/blueprints)
- [Weave GitOps OIDC Auth]
  (https://docs.gitops.weave.works/docs/configuration/oidc-access/)
- [Apache Guacamole Header Auth]
  (https://guacamole.apache.org/doc/gug/header-auth.html)
- [Traefik ForwardAuth]
  (https://doc.traefik.io/traefik/middlewares/http/forwardauth/)
