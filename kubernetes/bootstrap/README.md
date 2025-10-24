# Bootstrap Instructions

Bootstrap configuration for the Kubernetes cluster using Taskfile + Helmfile.

## Prerequisites

- `kubectl`, `task`, `helmfile`, `helm`, `kustomize`, `yq`
- `op` - 1Password CLI (authenticated)

## Directory Structure

```text
bootstrap/
├── README.md                          # This file
├── helmfile.d/                        # Helmfile configurations
│   ├── 00-crds.yaml                  # CRD extraction from charts
│   ├── 01-apps.yaml                  # Core bootstrap applications
│   └── templates/
│       └── values.yaml.gotmpl        # Values template (reads from apps/)
└── resources.yaml.j2                 # Bootstrap resources with 1Password refs
```

## Bootstrap Process

Run the complete bootstrap:

```bash
task bootstrap
```

Or run individual stages:

- `task bootstrap:wait` - Wait for nodes
- `task bootstrap:namespaces` - Apply namespaces
- `task bootstrap:resources` - Apply secrets (1Password injection)
- `task bootstrap:crds` - Apply CRDs
- `task bootstrap:apps` - Deploy core apps (cert-manager, external-secrets)

## 1Password Setup

Required secrets in the `kubernetes` vault:

- `1password`: `OP_CREDENTIALS_JSON`, `OP_CONNECT_TOKEN`
- `sops`: `SOPS_PRIVATE_KEY`

## Values

Bootstrap values are sourced from `kubernetes/apps/*/app/helmrelease.yaml`
to ensure consistency with Flux-managed deployments.

## Post-Bootstrap

After bootstrap, initialize Flux to manage remaining applications. See main
repository documentation for Flux setup.

## Troubleshooting

**CRD failures**: Check CRD generation output with
`helmfile -f kubernetes/bootstrap/helmfile.d/00-crds.yaml template -q`

**1Password auth**: `op whoami`

**Missing tools**: Tasks will fail with clear error messages

## Maintenance

Chart versions are in `helmfile.d/*.yaml`. Keep synced with
`kubernetes/apps/` HelmRelease definitions.

---

## First-Time Setup

For new cluster setup, create SOPS age key:

1. Generate: `age-keygen -o keys.txt`
2. Store private key in 1Password (`kubernetes/sops/SOPS_PRIVATE_KEY`)
3. Add public key to `.sops.yaml`
4. Create encrypted secret in `kubernetes/bootstrap/flux/age-key.secret.sops.yaml`

See repository setup documentation for detailed instructions.
