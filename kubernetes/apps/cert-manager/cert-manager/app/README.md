# Cert Manager

## Create secret necessary for bootstrap

Create `cloudflare-api-secret.yaml` with the following content:
Begin by cloning the sliver repo locally:

```bash
---
apiVersion: v1
kind: Secret
metadata:
  name: cloudflare-api-secret
type: Opaque
data:
  email: <base64 encoded email>
  CLOUDFLARE_API_KEY: <base64 encoded api key>
```

When creating the base64 encoded values, it is crucial to remove newlines
from the output. Use the `-n` flag with `echo` to accomplish this.

For example:

```bash
echo -n "your-cloudflare-account-email" | base64
echo -n $(op item get 'cloudflare-api-secret' --fields CLOUDFLARE_API_KEY) | base64
```

Once everything is running, be sure to delete the created
`cloudflare-api-secret.yaml` file:

```bash
rm cloudflare-api-secret.yaml
```
