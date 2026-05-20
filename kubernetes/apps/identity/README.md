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
    ┌────┴─────┬─────────────┬──────────────┬──────────────┬─────────┐
    ▼          ▼             ▼              ▼              ▼         ▼
┌─────────┐ ┌──────────┐ ┌────────────┐ ┌──────────┐ ┌─────────┐ ┌────────┐
│ Grafana │ │ Traefik  │ │ Guacamole  │ │  Weave   │ │Synology │ │ Immich │
│ (OAuth) │ │ (Forward)│ │  (Forward) │ │  GitOps  │ │   NAS   │ │ (OIDC) │
│         │ │          │ │            │ │  (OIDC)  │ │ (OIDC)  │ │        │
└─────────┘ └──────────┘ └────────────┘ └──────────┘ └─────────┘ └────────┘
```

## Configuration

### 1Password Setup

The deployment expects these secrets in the `authentik` 1Password item:

- **GRAFANA_CLIENT_SECRET** — OAuth2 client secret for Grafana
- **TRAEFIK_CLIENT_SECRET** — Forward auth secret for Traefik
- **WEAVE_GITOPS_CLIENT_SECRET** — OAuth2 client secret for Weave GitOps
- **GUACAMOLE_CLIENT_SECRET** — Forward auth secret for Guacamole
- **TAILSCALE_CLIENT_SECRET** — OAuth2 client secret for Tailscale
- **HOMEASSISTANT_CLIENT_SECRET** / **HOMEASSISTANT_TEST_CLIENT_SECRET**
- **SYNOLOGY_NAS_CLIENT_SECRET** — OIDC client secret for Synology NAS
- **IMMICH_CLIENT_SECRET** — OIDC client secret for Immich
- **AUTHENTIK_BOOTSTRAP_PASSWORD** — Admin password for initial setup
- **AUTHENTIK_BOOTSTRAP_TOKEN** — API token for automation
- **AUTHENTIK_SECRET_KEY** — Django secret key
- **AUTHENTIK_POSTGRESQL_PASSWORD** — Embedded PostgreSQL password
- **AUTHENTIK_USERS_BLUEPRINT** — user→group memberships (see [Add Users to Groups](#add-users-to-groups))

### Blueprint Configuration

Authentik uses blueprints to declaratively configure providers, applications,
groups, policies, and user/group memberships:

- `authentik-oauth-blueprint.yaml` — providers, applications, groups, policies
- `authentik-passkeys-blueprint.yaml` — passkey enrollment flow
- `externalsecret-users-blueprint.yaml` — user→group memberships
  (see [Add Users to Groups](#add-users-to-groups))

Discovered and applied by `authentik-worker` on deployment and on ConfigMap
change. Manual trigger if needed:

```bash
kubectl exec -n identity deploy/authentik-worker -- \
  ak apply_blueprint /blueprints/mounted/cm-authentik-oauth-blueprint/oauth-providers.yaml
```

### User Groups

Groups are defined declaratively in `authentik-oauth-blueprint.yaml`:

- **Grafana Admins** / **Grafana Editors**
- **Traefik Admins**
- **Weave GitOps Admins**
- **Guacamole Users**
- **Tailscale Users**
- **Home Assistant Admins** / **Home Assistant Users** (and Test variants)
- **NAS Admins** / **NAS Users**
- **AdGuard Admins**
- **Immich Users**

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

### Immich (OIDC)

- **Issuer URL**: `https://auth.techvomit.xyz/application/o/immich/`
  (trailing slash required)
- **Client ID**: `immich`
- **Redirect URIs**: `/auth/login`, `/user-settings`, `/api/oauth/mobile-redirect`,
  and `app.immich:///oauth-callback` (mobile deep link)
- **Required group**: `Immich Users`
- **Storage label claim**: `preferred_username`

The OIDC client secret lives on the `authentik-secrets` 1Password item as
`IMMICH_CLIENT_SECRET`. The `media` namespace receives a reflected copy of
the `authentik-secrets` Kubernetes Secret (via the
`reflector.v1.k8s.emberstack.com/reflection-allowed-namespaces` annotation
on the source ExternalSecret), and the Immich HelmRelease injects the
client secret into the Immich config Secret via Flux's `valuesFrom`
mechanism — Immich does **not** support `${VAR}` substitution in its
config file, so the secret is rendered into the Kubernetes Secret at
deploy time rather than expanded at container start.

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

User → group memberships live **entirely in 1Password**, in the
`AUTHENTIK_USERS_BLUEPRINT` field on the `authentik-secrets` item. ESO
renders that field into a Kubernetes Secret named `authentik-users-blueprint`
(via `externalsecret-users-blueprint.yaml`), which the authentik chart mounts
into the worker pod under `/blueprints/mounted/secret-authentik-users-blueprint/`.

The blueprint is the **single source of truth** — memberships added manually
through the Authentik UI will be pruned on the next reconcile (~60 min).

To grant a user access to a new application:

1. Pull the current value:

   ```bash
   op item get ochrsulp443vs2guyehbk6tqxe --vault automation \
     --fields label=AUTHENTIK_USERS_BLUEPRINT --format json \
     | jq -r '.value' > /tmp/users.yaml
   ```

2. Edit `/tmp/users.yaml`. Add or update the `authentik_core.user` entry,
   listing **every** group the user should be in (the `groups` list is
   replaced wholesale on each apply, not appended):

   ```yaml
   - model: authentik_core.user
     identifiers:
       username: alice
     state: present
     attrs:
       groups:
         - !Find [authentik_core.group, [name, "Immich Users"]]
         - !Find [authentik_core.group, [name, "Home Assistant Users"]]
   ```

3. Push it back:

   ```bash
   op item edit ochrsulp443vs2guyehbk6tqxe --vault automation \
     "AUTHENTIK_USERS_BLUEPRINT[text]=$(cat /tmp/users.yaml)"
   ```

4. ESO refreshes the Secret on its interval (~1h). To expedite, force a sync:

   ```bash
   kubectl -n identity annotate externalsecret authentik-users-blueprint \
     force-sync=$(date +%s) --overwrite
   ```

   authentik-worker discovers the new file content within a couple minutes
   and re-applies it.

Notes:

- `state: present` with no `password` attr preserves the existing password
  hash, MFA factors, and `last_login` across reconciles — safe to commit
  without exposing credentials.
- If a user doesn't yet exist, the entry creates them with no password; they
  then enroll via the recovery flow or an admin sets one in the UI once.
- The previous `authentik-group-sync` CronJob (which auto-added the admin
  user to every group) was retired when this blueprint was adopted.

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
