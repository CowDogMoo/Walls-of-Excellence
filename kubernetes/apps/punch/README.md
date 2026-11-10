# Punch

Serves the [Punch](https://github.com/l50/punch) web UI at
`https://punch.techvomit.xyz`. Punch doesn't run in the cluster: it runs on
bringer-of-despair, a Mac on the home network, and Traefik proxies to it.

## How a request reaches Punch

1. Traefik terminates TLS for `punch.techvomit.xyz` with the shared
   `techvomit-xyz-production-tls` wildcard certificate (`ingress.yaml`).
2. The `networking-authentik` forward-auth middleware sends the visitor through
   Authentik. Only members of the **Punch Users** group get past it.
3. Traefik connects to Punch's homelab listener at `192.168.20.35:7625` over
   HTTPS (`service.yaml`, manual Endpoints). It verifies Punch's server
   certificate against a private CA, expects the name `bringer-of-despair`, and
   presents a client certificate (`serverstransport.yaml`).
4. Punch's homelab listener refuses any connection without that client
   certificate, then trusts the `X-authentik-username` header Traefik forwards.
   Its loopback port 7624 is separate and isn't exposed.

## Prerequisites

The route returns an error until all of these are in place. Nothing else in the
cluster depends on them.

- **Punch homelab listener**: Punch on bringer-of-despair must ship the homelab
  TLS listener on port 7625 and have it turned on, with a server certificate
  for `bringer-of-despair` (SAN IP `192.168.20.35`) signed by the private CA.
- **DHCP reservation**: bringer-of-despair must keep `192.168.20.35`. The
  reservation lives in terraform-cowdogmoo.
- **1Password item**: `punch-homelab-mtls` in the `automation` vault, with
  fields `PUNCH_MTLS_CA_CRT`, `PUNCH_MTLS_CLIENT_CRT`, and
  `PUNCH_MTLS_CLIENT_KEY`. `externalsecret.yaml` renders them into the
  `punch-homelab-mtls` Secret that the ServersTransport reads.
- **Punch Users membership**: add the group to each user who needs access in
  the `AUTHENTIK_USERS_BLUEPRINT` field. See
  [Add Users to Groups](../identity/README.md#add-users-to-groups).
