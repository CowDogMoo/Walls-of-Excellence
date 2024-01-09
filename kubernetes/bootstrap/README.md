# Bootstrap Instructions

1. Navigate to the `kubernetes` directory.

2. Install flux

   ```bash
    kubectl apply --server-side --kustomize ./bootstrap
   ```

3. Install the age key

   ```bash
   sops -d bootstrap/age-key.sops.yaml | kubectl apply -f -
   ```

4. Start

   ```bash
   kubectl apply --server-side --kustomize flux-system/config
   ```
