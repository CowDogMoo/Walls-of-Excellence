# Encryption & Decryption with SOPS

WOE uses `sops` for encrypting and decrypting sensitive data,
particularly for Kubernetes secret management. Below is a summary of the key
steps and commands used in our setup.

## Overview

`sops` is a tool that encrypts each value in a file, allowing us to securely
store, manage, and share secrets in version control. In our case, we use `sops`
with `age` for encryption and decryption.

## Setting Up `sops`

1. **Installation**: `sops` can be installed on various platforms including
   Linux, macOS, and Windows. For installation instructions, refer to the
   [`sops` GitHub page](https://github.com/mozilla/sops).

2. **Encryption Keys**: We use `age` for encryption, which requires generating
   a key pair. Store the keys securely and ensure they are accessible for
   encryption and decryption processes.

## Retrieving Age Keys from 1password

Using the 1password CLI, you can get the age keys from the vault. For example:

```bash
op item get 'your age key'
```

## Encrypting YAML Content

1. **Prepare the YAML File**: Create a YAML file containing both the sensitive
   (to be encrypted) and non-sensitive data. If you're working with
   a Kubernetes secret, be sure to base64 encode the sensitive data.

2. **Selective Encryption**: Encrypt only specific fields in the YAML file,
   typically the fields containing sensitive data. For example:

   ```bash
   sops --encrypt --encrypted-regex '^(data)$' --age [your-age-public-key-recipient] onepassword-connect.secret.yaml > onepassword-connect.secret.sops.yaml
   ```

   This command encrypts only the data under the `data` field.

## Decrypt and Apply to Kubernetes

```bash
pushd kubernetes/apps/external-secrets/external-secrets/app ||  exit 1
sops -d onepassword-connect.secret.sops.yaml | kubectl apply -f -
popd || exit 1
```

## Editing Encrypted Files

To directly edit an encrypted file, use:

```bash
sops onepassword-connect.secret.sops.yaml
```

This opens the file in an editor, allowing for viewing and editing the
decrypted content. Upon saving and exiting, `sops` re-encrypts the file.

## Decrypting the Encrypted File

To decrypt the encrypted file, run the following commands:

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

## Example 1password-connect.secret.yaml (pre-encryption)

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

## Troubleshooting

- **Key File Location**: If `sops` cannot locate the `age` key file, set the
  `SOPS_AGE_KEY_FILE` environment variable to its path.

- **Errors in Decryption**: Ensure the correct decryption key is available and
  accessible. The file must be encrypted with `sops` and the same keys used for
  decryption.
