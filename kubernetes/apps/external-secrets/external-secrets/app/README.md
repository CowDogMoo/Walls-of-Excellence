# Managing sops external-secrets secret

## Decrypt and Apply to Kubernetes

```bash
pushd kubernetes/apps/external-secrets/external-secrets/app ||  exit 1
sops -d onepassword-connect.secret.sops.yaml | kubectl apply -f -
popd || exit 1
```

## Create the 1password-connect.secret.yaml file

1. You will need to create a dedicated vault using the
   1password web interface.

1. You will also need to create a custom connect server
   after, which will provide you with the `1password-credentials.json` file
   and the `token` to use with the connect server.

1. Retrieve your public key used to bootstrap the cluster. If using 1password,
   you can use the cli to get this information:

   ```bash
   op item get 'woe age key' --fields publicKey
   ```

1. Create `onepassword-connect.secret.yaml` - you will need to replace
   some of these values depending on your situation:

   ```bash
   cat <<EOF > onepassword-connect.secret.yaml
   ---
   # yamllint disable
   apiVersion: v1
   kind: Secret
   metadata:
     name: onepassword-connect-secret
     namespace: external-secrets
   stringData:
     # Pray to whatever deity you believe in if you don't base64 encode this
     # bad boy twice!!!
     1password-credentials.json: $(cat ~/Downloads/1password-credentials.json | base64 | base64)
     token: $(op item get 'woe Access Token: k8s' --fields credential | base64)
   EOF
   ```

1. Create the `onepassword-connect.secret.sops.yaml` file by running the
   following command:

   ```bash
   AGE_PUBLIC_KEY=age....
   sops --encrypt \
   --age $AGE_PUBLIC_KEY \
   onepassword-connect.secret.yaml > onepassword-connect.secret.sops.yaml
   ```

1. Delete the `onepassword-connect.secret.yaml` file:

   ```bash
   rm onepassword-connect.secret.yaml
   ```

---

## Miscellaneous Notes and Tidbits

### Troubleshooting

- **Key File Location**: If `sops` cannot locate the `age` key file, set the
  `SOPS_AGE_KEY_FILE` environment variable to its path.

- **Errors in Decryption**: Ensure the correct decryption key is available and
  accessible. The file must be encrypted with `sops` and the same keys used for
  encryption.

### Editing Encrypted Files

To directly edit an encrypted file, use:

```bash
sops onepassword-connect.secret.sops.yaml
```

This opens the file in an editor, allowing for viewing and editing the
decrypted content. Upon saving and exiting, `sops` re-encrypts the file.

### Decrypting encrypted files

To decrypt a sops encrypted file, run the following commands:

```bash
touch keys.txt
# populate keys.txt with the age private key
export SOPS_AGE_KEY_FILE=$(pwd)/keys.txt
sops -d --output onepassword-connect.secret.yaml onepassword-connect.secret.sops.yaml
```

At this point, we should have the decrypted `onepassword-connect.yaml`.

Run this command to set the 1p connect secret:

```bash
kubectl apply -f onepassword-connect.secret.yaml
```

Be sure to clean it up after you're done:

```bash
rm onepassword-connect.secret.yaml
```

### Pre-encryption 1password-connect.secret.yaml example

```yaml
---
apiVersion: v1
kind: Secret
metadata:
  name: onepassword-connect-secret
  namespace: external-secrets
stringData:
  1password-credentials.json: |
    {
      "verifier": {
        "salt": "...",
        "localHash": "...",
      },
      "encCredentials": {
        "kid": "...",
        ...
      },
      "version": "2",
      "deviceUuid": "...",
      "uniqueKey": {
        "alg": "A256GCM",
        "ext": true,
        "k": "...",
        "key_ops": [
          "encrypt",
          "decrypt"
        ],
        "kty": "...",
        "kid": "..."
      }
    }
  token: ey...
```
