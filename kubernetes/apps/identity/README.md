# Identity - Authentik SSO

Open-source Identity Provider providing Single Sign-On, OAuth2/OIDC, and
forward authentication for cluster applications.

## Overview

Authentik serves as the central authentication gateway for all services in
this Kubernetes cluster. It provides secure, group-based access control using
OAuth2, OIDC, and forward auth protocols while maintaining a seamless single
sign-on experience.

## Features

- **Single Sign-On (SSO)** - One login for all cluster services
- **Multiple Auth Protocols** - OAuth2, OIDC, and forward authentication
- **Group-Based Access Control** - Fine-grained permissions via group membership
- **Declarative Configuration** - Blueprint-based setup with Infrastructure as Code
- **Embedded Outpost** - No separate proxy deployment needed for forward auth
- **Automated Secret Management** - Integration with 1Password via External
  Secrets Operator

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
    ┌────┴─────┬─────────────┬──────────────┬──────────────┐
    ▼          ▼             ▼              ▼              ▼
┌─────────┐ ┌──────────┐ ┌────────────┐ ┌──────────┐ ┌─────────┐
│ Grafana │ │ Traefik  │ │ Guacamole  │ │  Weave   │ │Synology │
│ (OAuth) │ │ (Forward)│ │  (Forward) │ │  GitOps  │ │   NAS   │
│         │ │          │ │            │ │  (OIDC)  │ │ (OIDC)  │
└─────────┘ └──────────┘ └────────────┘ └──────────┘ └─────────┘
```

## Configuration

### 1Password Setup

The deployment expects these secrets in the `authentik` 1Password item:

- **grafana-client-secret**: OAuth2 client secret for Grafana
- **weave-gitops-client-secret**: OAuth2 client secret for Weave GitOps
- **synology-oidc-client-secret**: OIDC client secret for Synology NAS
- **AUTHENTIK_BOOTSTRAP_PASSWORD**: Admin password for initial setup
- **AUTHENTIK_BOOTSTRAP_TOKEN**: API token for automation
- **AUTHENTIK_SECRET_KEY**: Django secret key

### Blueprint Configuration

Authentik uses blueprints to declaratively configure providers, applications,
groups, and policies:

- **Location**: `kubernetes/apps/identity/authentik/app/authentik-oauth-blueprint.yaml`
- **Auto-applied**: On deployment by authentik-worker
- **Manual trigger**:

  ```bash
  kubectl exec -n identity deploy/authentik-worker -- \
    ak apply_blueprint /blueprints/mounted/cm-authentik-oauth-blueprint/oauth-providers.yaml
  ```

### User Groups

Navigate to https://auth.techvomit.xyz/if/admin/ and create/verify groups:

- **Grafana Admins** - Full Grafana access
- **Grafana Editors** - Editor access to Grafana
- **Traefik Admins** - Traefik dashboard access
- **Weave GitOps Admins** - GitOps dashboard access
- **Guacamole Users** - Remote desktop access
- **Synology NAS Users** - NAS access

## Deployment

### Prerequisites

- Kubernetes cluster (v1.29+)
- Flux GitOps deployed and configured
- Traefik ingress controller
- External Secrets Operator with 1Password integration
- Valid TLS certificates for auth.techvomit.xyz

### Installation

Deploy via Flux (automatic):

```bash
flux reconcile ks cluster-apps --with-source -n flux-system
```

Or manually apply:

```bash
kubectl apply -f kubernetes/apps/identity/authentik/app/
```

### Verification

```bash
# Check pods are running
kubectl get pods -n identity

# Verify blueprint applied
kubectl logs -n identity deploy/authentik-worker --tail=50 | grep blueprint
```

## Service Integration

### Weave GitOps (OIDC)

- **Issuer URL**: `https://auth.techvomit.xyz/application/o/weave-gitops/`
  (trailing slash required)
- **Client ID**: `weave-gitops`
- **Redirect URL**: `https://weave.techvomit.xyz/oauth2/callback`
- **Signing Algorithm**: RS256 with "authentik Internal JWT Certificate"

**Additional RBAC Required**: Edit
`kubernetes/apps/flux-system/weave-gitops/app/oidc-user-clusterrolebinding.yaml`
and add your email:

```yaml
subjects:
  - kind: User
    name: your-email@example.com
```

### Guacamole (Forward Auth + Header Auth)

**Forward Auth Flow**:

1. User requests https://guacamole.techvomit.xyz
2. Traefik forwards auth request to Authentik outpost
3. Authentik validates user and group membership
4. If authorized, Authentik returns headers including `X-authentik-username`
5. Traefik forwards request to Guacamole with headers
6. Guacamole reads header and auto-logs in user

**Header Configuration**: Automatically set via postStart lifecycle hook in deployment

### Synology NAS (OIDC)

**Provider Settings**:

- **Client ID**: `synology-nas`
- **Redirect URI**: `https://nas.techvomit.xyz/#/signin`
- **Token Validity**: Access Code (1m), Access Token (5m), Refresh Token (30d)

**DSM Setup**:

1. Log into DSM: https://nas.techvomit.xyz
2. Go to **Control Panel** → **Domain/LDAP** → **SSO Client**
3. Click **Add** → **OpenID Connect**
4. Configure:
   - Profile: Custom
   - Name: Authentik SSO
   - Authorization Endpoint: `https://auth.techvomit.xyz/application/o/authorize/`
   - Token Endpoint: `https://auth.techvomit.xyz/application/o/token/`
   - UserInfo Endpoint: `https://auth.techvomit.xyz/application/o/userinfo/`
   - Client ID: `synology-nas`
   - Client Secret: (from 1Password)
   - Redirect URL: `https://nas.techvomit.xyz/#/signin`
   - Username Claim: `preferred_username`
5. Enable **Auto-create users**
6. Test the connection

### Traefik Dashboard (Forward Auth)

Uses forward authentication similar to Guacamole. Access at https://traefik.techvomit.xyz

### Grafana (OAuth2)

OAuth2 authentication with role mapping from Authentik groups. Access at https://grafana.techvomit.xyz

## Operations

### View Logs

```bash
# Server logs
kubectl logs -n identity deploy/authentik-server -f

# Worker logs
kubectl logs -n identity deploy/authentik-worker -f
```

### Check Blueprint Status

```bash
kubectl logs -n identity deploy/authentik-worker | grep blueprint
```

### Add Users to Groups

1. Navigate to https://auth.techvomit.xyz/if/admin/
2. Go to **Directory** → **Users**
3. Select user
4. Click **Groups** tab
5. Add to appropriate groups

### Generate Client Secret

```bash
openssl rand -base64 32
```

Then add to 1Password under the `authentik` item.

## Troubleshooting

### Blueprint Not Applied

Check worker logs and manually apply:

```bash
kubectl logs -n identity deploy/authentik-worker --tail=100

kubectl exec -n identity deploy/authentik-worker -- \
  ak apply_blueprint /blueprints/mounted/cm-authentik-oauth-blueprint/oauth-providers.yaml
```

### Weave GitOps: "No Data" After Login

User lacks Kubernetes RBAC permissions. Add user email to `oidc-user-clusterrolebinding.yaml`.

### Guacamole: Still Shows Login Form

Verify header auth is configured:

```bash
kubectl exec -n guacamole deploy/guacamole -- \
  cat /config/guacamole/guacamole.properties | grep http-auth-header
```

Expected output: `http-auth-header: X-authentik-username`

### Synology NAS: SSO Connection Failed

Verify OIDC provider configuration:

```bash
kubectl exec -n identity deploy/authentik-server -- \
  ak list providers oauth2 | grep synology-nas
```

Check redirect URI matches exactly: `https://nas.techvomit.xyz/#/signin`

### OIDC Token Signing Errors

Error: `oidc: id token signed with unsupported algorithm, expected ["RS256"]
got "HS256"`

Ensure OAuth2 provider uses `signing_key` pointing to "authentik Internal JWT
Certificate" in the blueprint.

## Security Considerations

### Forward Auth Header Sanitization

**CRITICAL**: When using forward auth with header authentication, ensure the
`X-authentik-*` headers are stripped from untrusted requests. Traefik's
forward auth middleware handles this automatically - headers are ONLY added
after successful Authentik authentication.

**Never** expose services directly without the middleware, as users could
manually add headers to bypass authentication.

### Certificate Types

- **authentik Internal JWT Certificate** - For RS256 JWT signing (OAuth2/OIDC)
- **authentik Self-signed Certificate** - For TLS

Use the correct certificate for each purpose.

### Group-Based Access Control

All applications use group-based policies:

- No group membership = No access (401/403)
- Wrong group = No access
- Correct group = Authenticated and authorized

## Resources

- [Authentik Documentation](https://docs.goauthentik.io/)
- [Authentik Blueprints](https://docs.goauthentik.io/docs/terminology/blueprints)
- [Weave GitOps OIDC Auth](https://docs.gitops.weave.works/docs/configuration/oidc-access/)
- [Apache Guacamole Header Auth](https://guacamole.apache.org/doc/gug/header-auth.html)
- [Traefik ForwardAuth](https://doc.traefik.io/traefik/middlewares/http/forwardauth/)
- [Synology OIDC Configuration](https://kb.synology.com/en-br/DSM/tutorial/How_to_configure_SSO_Client)
