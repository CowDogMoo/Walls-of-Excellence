# Bootstrap Instructions

1. Install flux

   ```bash
   kubectl apply --server-side -k ./flux --force-conflicts
   kubectl apply -k ./flux
   ```

1. Add age key to the cluster

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
     age.agekey: $(cat keys.txt | grep "AGE-SECRET-KEY" | base64)
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
