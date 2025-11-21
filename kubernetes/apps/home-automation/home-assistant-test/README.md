# Home Assistant Test Instance

This is a test instance of Home Assistant configured to use Authentik for OIDC authentication.

## Setup Instructions

### 1. Generate Client Secret

Generate a secure client secret using openssl:

```bash
openssl rand -hex 32
```

### 2. Add Secret to 1Password

Add the following fields to the `home-assistant-test-secrets` item in 1Password:

- `HOMEASSISTANT_TEST_CLIENT_SECRET`: The generated secret from step 1

Also add the same value to the `authentik-secrets` item in 1Password:

- `HOMEASSISTANT_TEST_CLIENT_SECRET`: The same generated secret

### 3. Configure Home Assistant

Once the pod is running, you'll need to configure Home Assistant to use
Authentik for authentication.

Add the following to your Home Assistant `configuration.yaml`:

```yaml
homeassistant:
  auth_providers:
    - type: homeassistant
    - type: command_line
      command: /config/auth_external.sh
      meta: true

http:
  use_x_forwarded_for: true
  trusted_proxies:
    - 10.42.0.0/16 # Adjust to your cluster pod network CIDR
```

Create `/config/auth_external.sh`:

```bash
#!/bin/bash
# This script validates authentication from Authentik
# The authentik integration will pass user info via environment variables

# For now, just echo success - customize as needed
echo "Authentication successful"
exit 0
```

### 4. Configure Authentik OIDC in Home Assistant

In Home Assistant, you'll need to manually configure the Authentik provider:

1. Go to Settings > People > Users
2. Add a new user or edit an existing one
3. Enable "Allow person to login"
4. Configure the authentication provider:
   - Provider: Generic OAuth2
   - Client ID: `home-assistant-test`
   - Client Secret: (use the secret you generated)
   - Authorize URL: `https://auth.techvomit.xyz/application/o/authorize/`
   - Token URL: `https://auth.techvomit.xyz/application/o/token/`
   - Userinfo URL: `https://auth.techvomit.xyz/application/o/userinfo/`
   - Scopes: `openid email profile`

Alternatively, you can use the Home Assistant Authentik integration if available.

### 5. Add Users to Authentik Group

To grant users access to the test Home Assistant instance:

1. Log into Authentik at https://auth.techvomit.xyz
2. Go to Directory > Groups
3. Find "Home Assistant Test Users"
4. Add users to this group

## Key Differences from Production

- Hostname: `ha-test.techvomit.xyz` (vs `ha.techvomit.xyz`)
- NFS Path: `/volume1/k8s/home-assistant-test` (vs `/volume1/k8s/home-assistant`)
- Service Type: ClusterIP (vs LoadBalancer)
- Host Network: Disabled (vs enabled on production)
- No node affinity constraints

## Accessing the Test Instance

Once deployed, access the test instance at:

https://ha-test.techvomit.xyz

## Configuration Files

- HelmRelease: `kubernetes/apps/home-automation/home-assistant-test/app/helmrelease.yaml`
- External Secret: `kubernetes/apps/home-automation/home-assistant-test/app/externalsecret.yaml`
- Kustomization: `kubernetes/apps/home-automation/home-assistant-test/app/kustomization.yaml`
- Flux Kustomization: `kubernetes/apps/home-automation/home-assistant-test/ks.yaml`

## Authentik Configuration

The Authentik OIDC provider is configured via the blueprint at:

`kubernetes/apps/identity/authentik/app/authentik-oauth-blueprint.yaml`

Key details:

- Client ID: `home-assistant-test`
- Redirect URI: `https://ha-test.techvomit.xyz/auth/external/callback`
- Scopes: `openid`, `email`, `profile`
- Authentication Flow: Passwordless WebAuthn
- Authorization Flow: Explicit Consent
