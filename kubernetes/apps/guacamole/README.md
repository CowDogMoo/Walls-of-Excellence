# Apache Guacamole

Apache Guacamole is a clientless remote desktop gateway that supports
standard protocols like VNC, RDP, and SSH.

## Authentication

Guacamole uses **dual authentication**:

1. **Traefik Forward Auth via Authentik** - Initial SSO layer
2. **Header-based Authentication** - Automatic login using
   `X-authentik-username` header

## Architecture

```text
User → Traefik (Forward Auth) → Authentik → Guacamole (Header Auth) →
Remote Hosts
```

When a user accesses Guacamole:

1. Traefik intercepts the request
2. Traefik sends auth request to Authentik embedded outpost
3. Authentik verifies user is in "Guacamole Users" group
4. Authentik returns success with `X-authentik-username` header
5. Traefik forwards request to Guacamole with header
6. Guacamole reads header and automatically logs in user
7. User sees Guacamole home screen (no login form!)

## Setup

### Prerequisites

1. Authentik proxy provider configured for Guacamole
   (see `kubernetes/apps/identity/README.md`)
2. User added to "Guacamole Users" group in Authentik

### Configuration Files

- `guacamole-deployment.yaml` - Main deployment with header auth
- `guacamole-ingress.yaml` - Traefik ingress with Authentik middleware
- `guacamole-config.yaml` - ConfigMap for header auth configuration
- `guacamole-pvc.yaml` - Persistent storage for Guacamole database
- `guacamole-service.yaml` - ClusterIP service

## Header Authentication

The `auth-header` extension is enabled via:

1. **Extension JAR**: Pre-installed at
   `/config/guacamole/extensions/guacamole-auth-header-1.6.0.jar`
2. **Configuration**: Added to `guacamole.properties` via postStart
   lifecycle hook

```yaml
lifecycle:
  postStart:
    exec:
      command:
        - /bin/sh
        - -c
        - |
          sleep 10
          echo "http-auth-header: X-authentik-username" >> \
            /config/guacamole/guacamole.properties
```

## Access

- URL: https://guacamole.techvomit.xyz
- No manual login required - automatically authenticated via
  Authentik

## Adding Connections

After SSO login, configure remote desktop connections in Guacamole:

1. Click your username (top right)
2. Select "Settings"
3. Go to "Connections" tab
4. Click "New Connection"
5. Configure connection:
   - **Name**: Friendly name
   - **Protocol**: VNC, RDP, or SSH
   - **Hostname**: Target host IP/hostname
   - **Port**: Protocol port (3389 for RDP, 5900 for VNC, 22 for
     SSH)
   - **Username/Password**: Credentials for remote host

## Troubleshooting

### Still Shows Login Form

**Symptom**: After Authentik authentication, Guacamole shows a login
form.

**Possible Causes**:

1. **Not in "Guacamole Users" group**
   - Solution: Add user to group in Authentik admin interface

2. **Header auth not configured**
   - Check:

     ```bash
     kubectl exec -n guacamole deploy/guacamole -- \
       cat /config/guacamole/guacamole.properties | \
       grep http-auth-header
     ```

   - Should show: `http-auth-header: X-authentik-username`
   - If missing, restart pod:

     ```bash
     kubectl rollout restart deployment/guacamole -n guacamole
     ```

3. **Extension not loaded**
   - Check:

     ```bash
     kubectl exec -n guacamole deploy/guacamole -- \
       ls /config/guacamole/extensions/
     ```

   - Should show: `guacamole-auth-header-1.6.0.jar`

### Access Denied by Authentik

**Symptom**: 403 Forbidden from Authentik

**Cause**: User not in "Guacamole Users" group

**Solution**:

1. Log into Authentik admin: https://auth.techvomit.xyz/if/admin/
2. Go to Directory → Groups
3. Select "Guacamole Users"
4. Add your user

### Clear Browser Cache

If changes don't take effect:

1. Clear browser cache/cookies for `guacamole.techvomit.xyz`
2. Or open in incognito/private window

## Security Considerations

### Header Authentication Security

The `X-authentik-username` header is **only** added by Authentik's
outpost after successful authentication. The Traefik middleware
ensures:

1. All `X-authentik-*` headers from client requests are stripped
2. Only Authentik can add these headers
3. Headers are only added after group membership verification

**Critical**: Never expose Guacamole directly without the Authentik
middleware, as users could forge headers.

### Database Security

Guacamole uses an embedded PostgreSQL database stored in the PVC at
`/config`. Database credentials are auto-generated on first start and
stored in `guacamole.properties`.

### Remote Desktop Credentials

Credentials for remote desktop connections are stored in Guacamole's
PostgreSQL database. These are separate from SSO authentication.

## Advanced Configuration

### Adding TOTP 2FA

Uncomment in `guacamole-deployment.yaml`:

```yaml
env:
  - name: EXTENSIONS
    value: auth-header,auth-totp  # Add auth-totp
```

This enables TOTP 2FA for an additional authentication layer.

### Custom Extensions

Additional Guacamole extensions can be added by:

1. Mounting them in `/config/guacamole/extensions/`
2. Listing them in the `EXTENSIONS` environment variable

## Persistent Data

The PVC at `/config` contains:

- PostgreSQL database (`/config/postgresql/`)
- Guacamole configuration (`/config/guacamole/guacamole.properties`)
- Extension JARs (`/config/guacamole/extensions/`)

**Backup**: Important to backup the PVC as it contains all connection
configurations and user data.

## Resources

- [Apache Guacamole Documentation]
  (https://guacamole.apache.org/doc/gug/)
- [Header Authentication Extension]
  (https://guacamole.apache.org/doc/gug/header-auth.html)
- [Authentik Proxy Provider]
  (https://docs.goauthentik.io/docs/providers/proxy/)
