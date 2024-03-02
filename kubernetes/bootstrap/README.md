# Bootstrap Instructions

1. Install flux

   ```bash
   kubectl apply --server-side -k ./flux
   kubectl apply -k ./flux
   ```

1. Install the age key

   ```bash
   sops -d flux/age-key.secret.sops.yaml | kubectl apply -f -
   ```

1. Start the flux bootstrap process

   ```bash
   kubectl apply --server-side -k ../flux/config
   kubectl apply -k ../flux/config
   ```

1. Create the cluster settings ConfigMap

   ```bash
   kubectl apply -k ../flux/vars
   ```

1. Install the repositories and sync

   ```bash
   kubectl apply -k ../flux/repositories
   ```

---

## Create the age key

If you haven't created the `age` key yet, you can do so by doing the following:

```bash
cd flux
age-keygen -o keys.txt
```

## Encrypt the age key

After the age key is created, next you'll need to create a `sops` file to store
the `age` key:

```bash
# create age-key.secret.yaml
cat <<EOF > age-key.secret.yaml
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

Base64 encode the `age` key (everything starting with `AGE-SECRET-KEY-`) and
save the changes.

Encrypt the `age` key:

```bash
AGE_PUBLIC_KEY=age....
sops --encrypt \
--age $AGE_PUBLIC_KEY \
age-key.yaml > age-key.secret.sops.yaml
```

Delete the `age-key.secret.yaml` file:

```bash
rm age-key.secret.yaml
```
