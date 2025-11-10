# Tailscale Operator for Kubernetes

This directory contains the configuration for deploying the Tailscale Kubernetes Operator, which provides secure access to your Kubernetes cluster services via Tailscale's mesh VPN network.

**🔐 Authentication**: This implementation integrates with Authentik for Single Sign-On (SSO) using OIDC, allowing you to use your existing identity provider for Tailscale authentication.

## Architecture Decision

**Why Kubernetes over UDMP?**

We chose to run Tailscale in the Kubernetes cluster rather than on the UniFi Dream Machine Pro for several reasons:

1. **Native Integration**: The official Tailscale Kubernetes Operator provides seamless integration with K8s resources
2. **GitOps Workflow**: Managed through Flux alongside other cluster resources
3. **High Availability**: Runs as a deployment with multiple replicas across cluster nodes
4. **Service Exposure**: Direct access to cluster services without additional configuration
5. **Easier Management**: Uses Kubernetes-native CRDs rather than maintaining scripts on UDMP

## Components

### 1. Tailscale Operator (Helm Chart)

- Manages Tailscale devices within the cluster
- Handles authentication and device lifecycle
- Deployed via HelmRelease in `helmrelease.yaml`

### 2. Subnet Router (Connector)

- Advertises Kubernetes pod and service CIDRs to your tailnet
- Allows access to any service in the cluster from Tailscale devices
- Configured in `connector.yaml`

### 3. OAuth Credentials (ExternalSecret)

- Securely provides OAuth client credentials from 1Password
- Required for the operator to authenticate with Tailscale
- Managed in `externalsecret.yaml`

### 4. Authentik OIDC Integration

- Provides SSO authentication for Tailscale users
- Configured via Authentik blueprint in the identity namespace
- WebFinger service for OIDC discovery

## Prerequisites

This deployment uses **Authentik SSO** for user authentication. Before deploying, you need to:

### 1. Configure Authentik OIDC Provider

The Authentik blueprint (`kubernetes/apps/identity/authentik/app/authentik-oauth-blueprint.yaml`) has been updated to include the Tailscale OIDC provider configuration. This will automatically:

1. Create a Tailscale OAuth2/OpenID provider in Authentik
2. Create a "Tailscale Users" group for access control
3. Create a Tailscale application with the slug `tailscale`
4. Configure proper redirect URIs and token validity

**Required 1Password Secret:**

Add a new field to your `authentik-secrets` item in 1Password:

- **Field Name**: `TAILSCALE_CLIENT_SECRET`
- **Value**: Generate a secure random string (e.g., using `openssl rand -base64 32`)

The blueprint will use `client_id: tailscale` and the secret you provide.

### 2. Deploy WebFinger Service

The WebFinger service (`kubernetes/apps/identity/authentik-webfinger/`) has been configured and will be deployed automatically. This service:

- Runs at `https://techvomit.xyz/.well-known/webfinger`
- Enables Tailscale to discover your Authentik OIDC provider
- Uses the `ghcr.io/sudo-kraken/authentik-webfinger-proxy` container
- Automatically configures the issuer URL pointing to `https://auth.techvomit.xyz`

No additional configuration needed - it will deploy alongside Authentik.

### 3. Add Users to Tailscale Group in Authentik

After deployment:

1. Log into Authentik at `https://auth.techvomit.xyz`
2. Go to **Directory** → **Groups**
3. Find the **Tailscale Users** group (auto-created by blueprint)
4. Add users who should have access to Tailscale

### 4. Configure Tailscale for Authentik SSO

Instead of the standard OAuth setup, you'll use custom OIDC:

**Skip this section if using Authentik SSO** - The OAuth Client creation described below is only needed for device authentication (the Kubernetes operator), not for user authentication which uses Authentik.

1. Go to the [Tailscale Admin Console](https://login.tailscale.com/admin/settings/oauth)
2. Navigate to **Settings** → **OAuth clients**
3. Click **Generate OAuth client**
4. Configure the OAuth client:
   - **Scopes**:
     - `devices:write` (Required for creating/managing devices)
     - `auth_keys:write` (Required for creating auth keys)
   - **Tags**: Add `tag:k8s-operator` as an owner tag
5. Copy the **Client ID** and **Client Secret** (you won't be able to see the secret again)

### 2. Configure Tailscale ACL Tags

In your tailnet policy file (Settings → ACL):

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

This configuration:

- Creates the required tags
- Allows the operator to manage devices with `tag:k8s`
- Permits your Tailscale users to access the subnet router

### 3. Store Credentials in 1Password

Create a new item in 1Password with:

- **Item Name**: `tailscale-oauth`
- **Fields**:
  - `client_id`: Your OAuth Client ID
  - `client_secret`: Your OAuth Client Secret

The ExternalSecret will automatically sync these credentials to Kubernetes.

### 3a. Setting Up Your Tailnet with Authentik SSO

**First-Time Tailnet Setup:**

If you're creating a new Tailnet or migrating to custom OIDC:

1. Go to [https://login.tailscale.com/start](https://login.tailscale.com/start)
2. Select **Sign up with OIDC**
3. Enter your email address using your domain: `user@techvomit.xyz`
4. Tailscale will query the WebFinger endpoint at `https://techvomit.xyz/.well-known/webfinger`
5. Enter the OIDC credentials:
   - **Client ID**: `tailscale` (from Authentik blueprint)
   - **Client Secret**: The value you stored in 1Password as `TAILSCALE_CLIENT_SECRET`
6. You'll be redirected to Authentik for authentication
7. After successful authentication, your tailnet will be created

**Adding Users to Existing Tailnet:**

Users can log in by:

1. Going to [https://login.tailscale.com](https://login.tailscale.com)
2. Entering their `@techvomit.xyz` email address
3. Being redirected to Authentik for authentication
4. Must be a member of the "Tailscale Users" group in Authentik

**Important Notes:**

- If you have an existing tailnet with a different identity provider, contact Tailscale support to migrate to custom OIDC
- All users must have email addresses on the `techvomit.xyz` domain (or configure additional domains in the WebFinger service)
- The WebFinger service must be publicly accessible for Tailscale to discover your OIDC provider

### 4. Verify Cluster Network CIDRs

The default configuration assumes standard K3s CIDRs:

- Pod CIDR: `10.42.0.0/16`
- Service CIDR: `10.43.0.0/16`

To verify your cluster's actual CIDRs:

```bash
# Check pod CIDR
kubectl cluster-info dump | grep -m 1 cluster-cidr

# Check service CIDR
kubectl cluster-info dump | grep -m 1 service-cluster-ip-range
```

If your cluster uses different CIDRs, update `connector.yaml`:

```yaml
spec:
  subnetRouter:
    advertiseRoutes:
      - "YOUR_POD_CIDR"
      - "YOUR_SERVICE_CIDR"
```

## Deployment

This configuration is managed by Flux. Once merged to the main branch:

1. Flux will automatically detect the changes
2. The operator will be deployed to the `networking` namespace
3. The subnet router will register as a device in your tailnet
4. Routes will need to be approved (see Post-Deployment)

## Post-Deployment Steps

### 1. Approve Subnet Routes

After deployment, the subnet router will appear in your Tailscale admin console but routes won't be active yet:

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

From a Tailscale-connected device:

```bash
# Test connectivity to a cluster service
# Get a service IP first
kubectl get svc -A

# Try to access it (example with a HTTP service)
curl http://10.43.x.x:port

# Or use DNS if the service has it configured
curl http://service-name.namespace.svc.cluster.local
```

## Accessing Cluster Services

Once configured, you can access cluster services by:

1. **Service ClusterIP**: Direct access to any service's cluster IP
2. **Pod IPs**: Direct access to individual pods (useful for debugging)
3. **Service DNS** (if DNS is configured): `service-name.namespace.svc.cluster.local`

Example accessing Traefik dashboard:

```bash
# Find the service IP
kubectl get svc -n networking traefik

# Access it directly via Tailscale
curl http://10.43.x.x:9000/dashboard/
```

## Troubleshooting

### Operator pod not starting

```bash
# Check operator logs
kubectl logs -n networking -l app.kubernetes.io/name=tailscale-operator

# Verify OAuth secret exists
kubectl get secret -n networking tailscale-operator-oauth
```

### Routes not appearing in Tailscale

```bash
# Check connector status
kubectl describe connector -n networking subnet-router

# Check for events
kubectl get events -n networking --sort-by='.lastTimestamp'
```

### Cannot access cluster services

1. Verify routes are approved in Tailscale admin console
2. Verify client has `--accept-routes` enabled
3. Check if services are actually running: `kubectl get pods -A`
4. Verify no NetworkPolicies are blocking access

### Connector keeps recreating

Check the operator logs and verify:

1. OAuth credentials are correct
2. Tags are properly configured in ACL
3. The operator has necessary permissions

### Authentik SSO Issues

**WebFinger endpoint not responding:**

```bash
# Test WebFinger endpoint
curl "https://techvomit.xyz/.well-known/webfinger?resource=acct:user@techvomit.xyz"

# Should return JSON with Authentik issuer URL
# Expected response includes: "https://auth.techvomit.xyz/application/o/tailscale/"

# Check WebFinger pod logs
kubectl logs -n identity -l app.kubernetes.io/name=authentik-webfinger

# Verify WebFinger service is running
kubectl get pods -n identity -l app.kubernetes.io/name=authentik-webfinger
```

**Tailscale can't find OIDC provider:**

1. Verify WebFinger ingress is configured correctly:

   ```bash
   kubectl get ingress -n identity authentik-webfinger
   ```

2. Ensure the ingress has a valid TLS certificate
3. Check that DNS is resolving `techvomit.xyz` to your cluster
4. Verify Authentik is accessible at `https://auth.techvomit.xyz`

**Users can't authenticate:**

1. Verify user is in "Tailscale Users" group in Authentik
2. Check Authentik application logs:

   ```bash
   kubectl logs -n identity -l app.kubernetes.io/name=authentik -c server
   ```

3. Verify the Tailscale provider is active in Authentik:
   - Log into Authentik admin
   - Go to Applications → Applications
   - Find "Tailscale" application
   - Verify it's enabled and properly configured
4. Check that the `TAILSCALE_CLIENT_SECRET` in 1Password matches what you configured in Tailscale

**OIDC credentials don't match:**

If you see authentication errors:

1. Verify the Client ID is `tailscale` (from the Authentik blueprint)
2. Verify the Client Secret matches between:
   - 1Password field `TAILSCALE_CLIENT_SECRET` in `authentik-secrets`
   - What you entered in Tailscale OIDC setup
3. Restart Authentik pods if you updated the secret:

   ```bash
   kubectl rollout restart deployment -n identity authentik-server
   kubectl rollout restart deployment -n identity authentik-worker
   ```

## Security Considerations

1. **SSO Integration**: Users authenticate through Authentik, providing centralized identity management
2. **Group-Based Access**: Only users in the "Tailscale Users" group can authenticate
3. **Least Privilege**: The operator only has permissions to manage its own resources
4. **OAuth Scoping**: OAuth client is scoped to only necessary permissions
5. **Tag-Based Access**: ACLs use tags to control which users can access the subnet router
6. **Network Policies**: Consider implementing NetworkPolicies to further restrict what the subnet router can access
7. **WebFinger TLS**: The WebFinger endpoint must use valid TLS for Tailscale to trust it

## Additional Resources

- [Tailscale Kubernetes Operator Documentation](https://tailscale.com/kb/1236/kubernetes-operator)
- [Deploy Subnet Routers on Kubernetes](https://tailscale.com/kb/1441/kubernetes-operator-connector)
- [Tailscale Custom OIDC Documentation](https://tailscale.com/kb/1240/sso-custom-oidc)
- [Authentik Tailscale Integration](https://integrations.goauthentik.io/networking/tailscale/)
- [Tailscale ACL Documentation](https://tailscale.com/kb/1018/acls)
- [K3s Network Configuration](https://docs.k3s.io/installation/network-options)

## Exit Node Configuration (Optional)

To use the cluster as a Tailscale exit node, uncomment in `connector.yaml`:

```yaml
spec:
  exitNode: true
```

This allows you to route all your internet traffic through the cluster's network connection.

## Maintenance

The operator will automatically:

- Renew auth keys before expiration
- Update device information in Tailscale
- Handle pod restarts and IP changes
- Clean up devices when connectors are deleted

No manual maintenance is typically required.
