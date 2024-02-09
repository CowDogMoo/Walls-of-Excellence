# Bootstrap Instructions

1. Navigate to the `kubernetes` directory.

1. Install flux

   ```bash
   kubectl apply --server-side --kustomize ./flux
   ```

1. Install the age key

   ```bash
   sops -d flux/age-key.sops.yaml | kubectl apply -f -
   ```

1. Delete `not-used` `NetworkPolicy`

   ```bash
   cd ~/cowdogmoo/woe/kubernetes/bootstrap/flux
   kubectl apply -k .
   ```

1. Start the flux bootstrap process

   ```bash
   kubectl apply --server-side --kustomize ../flux-system/config
   ```

1. Install the repositories and sync

   ```bash
   cd ~/cowdogmoo/woe/kubernetes/flux-system/config
   kubectl apply -k .
   cd ~/cowdogmoo/woe/kubernetes/flux-system/repositories
   kubectl apply -k .
   ```

## Encrypt the age key

If you haven't created the `age` key yet, you can do so by doing the following:

````bash
touch flux/age-key.sops.yaml

# create flux/age-key.sops.yaml
cat <<EOF > flux/age-key.sops.yaml
---
# yamllint disable
apiVersion: v1
kind: Secret
metadata:
    name: sops-age
    namespace: flux-system
stringData:
  age.agekey: AGE-SECRET-KEY-
EOF
```

Then, encrypt the `age` key:

```bash
AGE_PUBLIC_KEY=age....
sops --encrypt \
--age $AGE_PUBLIC_KEY \
age-key.sops.yaml > age-key.sops.yaml
````
