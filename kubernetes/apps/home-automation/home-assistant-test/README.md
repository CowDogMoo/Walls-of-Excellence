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

### 3. Configure Home Assistant OIDC Authentication

The deployment automatically installs the
[hass-oidc-auth](https://github.com/christiaangoossens/hass-oidc-auth) custom
component and configures the necessary secrets. Once the pod is running, you
need to add the OIDC auth provider to your Home Assistant configuration.

#### Automatic Configuration (Applied by Init Containers)

The following are automatically configured:

- **OIDC Component**: The `install-oidc-component` init container installs
  the `auth_oidc` custom component to `/config/custom_components/auth_oidc/`
- **Secrets**: The `setup-oidc` init container creates
  `/config/secrets.yaml` with your Authentik client secret
- **HTTP Proxy Settings**: Reverse proxy configuration for Traefik is
  automatically added to `configuration.yaml`

#### Manual Configuration Required

Add the OIDC auth provider to your Home Assistant `configuration.yaml`:

```yaml
homeassistant:
  auth_providers:
    - type: homeassistant
    - type: auth_oidc
      id: authentik
      name: Authentik
      domain: auth.techvomit.xyz
      client_id: home-assistant-test
      client_secret: !secret authentik_client_secret
      auth_url: https://auth.techvomit.xyz/application/o/authorize/
      token_url: https://auth.techvomit.xyz/application/o/token/
      userinfo_url: https://auth.techvomit.xyz/application/o/userinfo/
      scopes:
        - openid
        - email
        - profile
        - groups
```

**Note**: The `http` configuration for reverse proxy trust is automatically
added if not present, so you don't need to manually configure it unless
customizing the trusted proxy CIDRs.

### 4. Add Users to Authentik Group

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
- Redirect URI: `https://ha-test.techvomit.xyz/auth/oidc/callback`
- Scopes: `openid`, `email`, `profile`, `groups`
- Authentication Flow: Passwordless WebAuthn
- Authorization Flow: Explicit Consent
- Custom Scope Mapping: Provides `is_admin` and `groups` fields for authorization
