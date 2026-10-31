# Flux Web UI

The [Flux Operator Web UI](https://fluxoperator.dev/web-ui/) at
<https://flux.techvomit.xyz>. It runs as a standalone `flux-web` release of
the flux-operator chart (`web.serverOnly`), so the operator itself never
depends on Authentik.

## Access

Login goes through the Authentik OIDC application `flux-web`. Authentik only
lets members of the **Flux Admins** group in, and the same group name arrives
in the `groups` claim, which the UI impersonates for Kubernetes RBAC.
`clusterrolebinding.yaml` binds that group to `flux-web-admin`, so admins can
view everything and reconcile, suspend, resume or restart workloads.

Group membership lives in the `AUTHENTIK_USERS_BLUEPRINT` field of the
`authentik-secrets` 1Password item, not in git.

To check what a user can do:

```bash
kubectl auth can-i reconcile kustomizations.kustomize.toolkit.fluxcd.io \
  --as=user@example.com --as-group="Flux Admins" -n flux-system
```

## Configuration

- `helmrelease.yaml`: web config, ingress, and the OIDC client secret
  (`FLUX_WEB_CLIENT_SECRET` from the reflected `authentik-secrets` Secret)
- `clusterrolebinding.yaml`: Flux Admins to `flux-web-admin`

The `flux-web-user` and `flux-web-admin` ClusterRoles come from the
flux-operator release, which still serves its own unauthenticated read-only
UI on port 9080 inside the cluster. Nothing routes to it from outside.

```bash
kubectl port-forward -n flux-system svc/flux-operator 9080:9080
```
