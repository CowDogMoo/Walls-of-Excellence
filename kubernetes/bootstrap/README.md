# Bootstrap Instructions

Navigate to the bootstrap directory (`kubernetes/bootstrap`) and do the following:

1. Install flux

   ```bash
   kubectl apply -k ./flux
   ```

1. Add age key to the cluster

   ```bash
   export SOPS_AGE_KEY_FILE='/path/to/generated/keys/file/from/age/keys.txt'
   sops -d flux/age-key.secret.sops.yaml | kubectl apply -f -
   ```

1. Start the flux bootstrap process

   ```bash
   kubectl apply --server-side -k ../flux/config
   kubectl apply -k ../flux/config
   ```

1. Create the cluster settings ConfigMap and configure sops

   ```bash
   kubectl apply --server-side -f ../flux/apps.yaml
   kubectl apply -f ../flux/apps.yaml
   kubectl apply -k ../flux/vars
   ```

1. Install the repositories and sync

   ```bash
   kubectl apply -k ../flux/repositories
   ```

1. Add all of the k8s apps to the cluster:

   ```bash
   cd ../apps
   find . -type f -name "kustomization.yaml" -execdir kubectl apply -k . \;
   ```

---

## Initial Creation of the age key

1. Create the `age` key:

   ```bash
   cd flux
   age-keygen -o keys.txt
   ```

1. Create `age-key.secret.yaml` with the following content:

   ```bash
   cat <<EOF > age-key.secret.yaml
   ---
   # yamllint disable
   apiVersion: v1
   kind: Secret
   metadata:
       name: sops-age
       namespace: flux-system
   stringData:
     age.agekey: $(cat keys.txt | grep -i "AGE-SECRET-KEY" | base64)
   EOF
   ```

1. Create the `age-key.secret.sops.yaml` file by running the
   following command:

   ```bash
   AGE_PUBLIC_KEY=age....
   sops --encrypt \
   --age $AGE_PUBLIC_KEY \
   age-key.secret.yaml > age-key.secret.sops.yaml
   ```

1. Delete the `age-key.secret.yaml` file:

   ```bash
   rm age-key.secret.yaml
   ```
