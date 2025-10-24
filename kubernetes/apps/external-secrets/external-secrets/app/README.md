# Managing 1Password Connect Secret

The 1Password Connect secret is managed through the bootstrap process using
1Password CLI injection, not SOPS encryption.

## Bootstrap Secret Management

The secret is defined in `kubernetes/bootstrap/resources.yaml.j2` and applied
during the bootstrap process:

```yaml
---
apiVersion: v1
kind: Secret
metadata:
  name: onepassword-secret
  namespace: external-secrets
stringData:
  1password-credentials.json: op://automation/onepassword-connect-secret/1password-credentials.json
  token: op://automation/1password-access-token-secret/credential
```

## Prerequisites

1. **1Password Vault**: Create a dedicated vault named "automation" using the
   1Password web interface.

2. **1Password Connect Server**: Create a custom connect server in 1Password,
   which provides:
   - `1password-credentials.json` file
   - Connect token for API access

## Setting Up 1Password Items

### 1. Store the Connect Token

Create or update the 1Password item for the connect token:

```bash
op item create \
  --category=password \
  --title='1password-access-token-secret' \
  --vault=automation \
  credential='<your-connect-token>'
```

### 2. Store the Credentials File (Base64-encoded)

**Important**: The credentials file must be base64-encoded before storing in
1Password to prevent double-decoding issues with the Connect API.

```bash
# Base64-encode the credentials file in place (without line wraps)
base64 < ~/Downloads/1password-credentials.json | tr -d '\n' > ~/Downloads/1password-credentials.json

# Create the 1Password item with the encoded credentials
op item create \
  --category=document \
  --title='onepassword-connect-secret' \
  --vault=automation \
  1password-credentials.json="$(cat ~/Downloads/1password-credentials.json)"
```

Or update an existing item:

```bash
# Base64-encode and copy to clipboard
base64 < ~/Downloads/1password-credentials.json | tr -d '\n' | pbcopy

# Update the item using 1Password app or CLI
op item edit onepassword-connect-secret \
  --vault=automation \
  1password-credentials.json="$(pbpaste)"
```

## Applying the Secret

The secret is automatically created during the bootstrap process:

```bash
task bootstrap:resources
```

This command:

1. Injects values from 1Password using `op inject`
2. Applies the secret to the cluster

## Manual Secret Application

If you need to manually apply the secret:

```bash
# Generate the secret with injected values
op inject -i kubernetes/bootstrap/resources.yaml.j2 | kubectl apply -f -
```

## Verifying the Secret

Check that the secret exists and has the correct keys:

```bash
kubectl get secret -n external-secrets onepassword-secret
kubectl describe secret -n external-secrets onepassword-secret
```

Verify the ClusterSecretStore is ready:

```bash
kubectl get clustersecretstore onepassword-connect
```

Should show:

```text
NAME                  AGE   STATUS   CAPABILITIES   READY
onepassword-connect   ...   Valid    ReadWrite      True
```

## Troubleshooting

### ClusterSecretStore Not Ready

If the ClusterSecretStore shows `InvalidProviderConfig`:

1. Check the onepassword pods are running:

   ```bash
   kubectl get pods -n external-secrets -l app.kubernetes.io/name=onepassword
   ```

2. Check the logs for errors:

   ```bash
   kubectl logs -n external-secrets -l app.kubernetes.io/name=onepassword -c sync --tail=50
   kubectl logs -n external-secrets -l app.kubernetes.io/name=onepassword -c api --tail=50
   ```

3. Verify the secret has the correct keys:

   ```bash
   kubectl get secret -n external-secrets onepassword-secret -o jsonpath='{.data}' | jq 'keys'
   ```

### Base64 Encoding Errors

If you see "illegal base64 data at input byte X" errors in the logs:

The credentials file in 1Password must be **base64-encoded**. This is because:

1. Kubernetes automatically base64-encodes secret data
2. Kubernetes automatically base64-decodes when mounting as environment
   variable
3. 1Password Connect expects the credentials to still be base64-encoded so it
   can decode them

Re-encode the credentials file following the steps in "Store the Credentials
File" above.

### ExternalSecret Not Syncing

If ExternalSecrets show `SecretSyncedError`:

1. Verify the 1Password item exists in the correct vault:

   ```bash
   op item list --vault=automation
   ```

2. Check the ExternalSecret definition matches the 1Password item structure:

   ```bash
   kubectl get externalsecret <name> -n <namespace> -o yaml
   ```

3. Check the external-secrets controller logs:

   ```bash
   kubectl logs -n external-secrets -l app.kubernetes.io/name=external-secrets --tail=50
   ```
