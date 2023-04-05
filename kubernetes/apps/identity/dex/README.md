# Dex

## Generate oauth secrets

1. Run this twice:

   ```bash
   openssl rand -base64 32
   ```

2. Use the output to set `DEX_OAUTH2_PROXY_CLIENT_ID`
   and `DEX_OAUTH2_PROXY_CLIENT_SECRET` in `oauth2-proxy-secret.yaml`
