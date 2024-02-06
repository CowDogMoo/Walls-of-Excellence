# Bootstrap Instructions

1. Navigate to the `kubernetes` directory.

1. Install flux

   ```bash
    kubectl apply --server-side --kustomize ./bootstrap
   ```

1. Install the age key

   ```bash
   sops -d bootstrap/age-key.sops.yaml | kubectl apply -f -
   ```

1. Delete `not-used` `NetworkPolicy`

   ```bash
   cd ~/cowdogmoo/woe/kubernetes/bootstrap
   kubectl apply -k .
   ```

1. Start the flux bootstrap process

   ```bash
   kubectl apply --server-side --kustomize flux-system/config
   ```

1. Install the repositories and sync

   ```bash
   cd ~/cowdogmoo/woe/kubernetes/flux-system/config
   kubectl apply -k .
   cd ~/cowdogmoo/woe/kubernetes/flux-system/repositories
   kubectl apply -k .
   ```
