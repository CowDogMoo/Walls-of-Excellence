# Tailscale Operator for Kubernetes

Tailscale Kubernetes Operator provides secure access to cluster services via
Tailscale's mesh VPN, integrated with Authentik SSO for user authentication.

## Components

- **Tailscale Operator** - Manages devices and authentication (`helmrelease.yaml`)
- **Subnet Router** - Advertises pod/service CIDRs to tailnet (`connector.yaml`)
- **OAuth Credentials** - ExternalSecret from 1Password (`externalsecret.yaml`)
- **Authentik OIDC** - SSO authentication with WebFinger discovery

## Prerequisites

### 1. Authentik OIDC Configuration

The Authentik blueprint
(`kubernetes/apps/identity/authentik/app/authentik-oauth-blueprint.yaml`)
auto-creates:

- Tailscale OAuth2/OIDC provider
- "Tailscale Users" group
- Application with slug `tailscale`

**Required 1Password Secret:**

Add to `authentik-secrets` item:

- **Field**: `TAILSCALE_CLIENT_SECRET`
- **Value**: `openssl rand -base64 32`

### 2. Tailscale OAuth Client (Operator Authentication)

Create OAuth client for the Kubernetes operator:

1. Go to [Tailscale Admin Console](https://login.tailscale.com/admin/settings/oauth)
2. Generate OAuth client with scopes:
   - `devices:write`
   - `auth_keys:write`
3. Tag: `tag:k8s-operator`

**Store in 1Password** (`tailscale-oauth` item):

- `client_id`
- `client_secret`

### 3. Tailscale ACL Configuration

```json
{
  "tagOwners": {
    "tag:k8s": ["tag:k8s-operator"],
    "tag:k8s-operator": ["your-email@example.com"],
    "tag:subnet-router": ["tag:k8s-operator"]
  },
  "acls": [
    {
      "action": "accept",
      "src": ["autogroup:members"],
      "dst": ["tag:k8s:*", "tag:subnet-router:*"]
    }
  ]
}
```

### 4. User Authentication Setup

**First-Time Tailnet:**

1. Go to https://login.tailscale.com/start
2. Select **Sign up with OIDC**
3. Enter email: `user@techvomit.xyz`
4. Enter credentials:
   - Client ID: `tailscale`
   - Client Secret: From 1Password `TAILSCALE_CLIENT_SECRET`
5. Authenticate via Authentik

**Add Users:**

1. Log into Authentik: https://auth.techvomit.xyz
2. Navigate: **Directory** → **Groups** → **Tailscale Users**
3. Add users to group

**WebFinger Discovery:**

The WebFinger service (`kubernetes/apps/identity/authentik-webfinger/`) is
auto-deployed and enables OIDC discovery at
`https://techvomit.xyz/.well-known/webfinger`.

## Post-Deployment

### 1. Approve Subnet Routes

After deployment, the subnet router will appear in your Tailscale admin console
but routes won't be active yet:

1. Go to the [Machines page](https://login.tailscale.com/admin/machines)
2. Find the device named `woe-k8s-subnet-router`
3. Click on it and go to the **Route settings** section
4. Click **Edit route settings**
5. Enable the advertised routes:
   - `10.42.0.0/16` (pods)
   - `10.43.0.0/16` (services)
6. Save the changes

### 2. Enable Route Acceptance on Client Devices

On any device you want to access the cluster from:

```bash
# macOS/Linux
sudo tailscale up --accept-routes

# Windows (PowerShell as Administrator)
tailscale up --accept-routes
```

Or enable "Use subnet routes" in the Tailscale GUI on macOS/Windows.

### 3. Verify Connectivity

```bash
# Get service IPs
kubectl get svc -A

# Access via ClusterIP
curl http://10.43.x.x:port

# Or via service DNS
curl http://service-name.namespace.svc.cluster.local
```

## Troubleshooting

### Operator Not Starting

```bash
# Check logs
kubectl logs -n networking -l app.kubernetes.io/name=tailscale-operator

# Verify OAuth secret
kubectl get secret -n networking tailscale-operator-oauth
```

### Routes Not Appearing

```bash
# Check connector status
kubectl describe connector -n networking subnet-router

# Check events
kubectl get events -n networking --sort-by='.lastTimestamp'
```

### Cannot Access Services

1. Verify routes approved in Tailscale admin console
2. Client has `--accept-routes` enabled
3. Services are running: `kubectl get pods -A`
4. No NetworkPolicies blocking access

### Connector Recreating

Verify:

1. OAuth credentials correct
2. ACL tags properly configured
3. Operator has necessary permissions

### WebFinger Not Responding

```bash
# Test endpoint
curl "https://techvomit.xyz/.well-known/webfinger?resource=acct:user@techvomit.xyz"

# Check logs
kubectl logs -n identity -l app.kubernetes.io/name=authentik-webfinger
```

### Users Can't Authenticate

1. User in "Tailscale Users" group in Authentik
2. Check Authentik logs:
   `kubectl logs -n identity -l app.kubernetes.io/name=authentik -c server`
3. Verify Tailscale application enabled in Authentik admin
4. `TAILSCALE_CLIENT_SECRET` matches between 1Password and Tailscale

### OIDC Credential Mismatch

If authentication fails:

1. Client ID is `tailscale`
2. Client Secret matches in 1Password and Tailscale
3. Restart Authentik if secret updated:

   ```bash
   kubectl rollout restart deployment -n identity authentik-server authentik-worker
   ```

## Security Considerations

- **SSO Integration**: Centralized identity management via Authentik
- **Group-Based Access**: "Tailscale Users" group membership required
- **Tag-Based ACLs**: Controls subnet router access
- **OAuth Scoping**: Minimal required permissions only
- **WebFinger TLS**: Valid TLS certificate required for OIDC discovery

## References

- [Tailscale Kubernetes Operator](https://tailscale.com/kb/1236/kubernetes-operator)
- [Subnet Routers on Kubernetes](https://tailscale.com/kb/1441/kubernetes-operator-connector)
- [Tailscale Custom OIDC](https://tailscale.com/kb/1240/sso-custom-oidc)
- [Authentik Tailscale Integration](https://integrations.goauthentik.io/networking/tailscale/)
- [Tailscale ACLs](https://tailscale.com/kb/1018/acls)
