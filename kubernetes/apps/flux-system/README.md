# flux-system

## weave-gitops

Install gitops CLI:

```bash
curl --silent --location "https://github.com/weaveworks/weave-gitops/releases/download/v0.20.0/gitops-$(uname)-$(uname -m).tar.gz" | tar xz -C /tmp
sudo mv /tmp/gitops /usr/local/bin
gitops version
```

Create password:

```bash
PASSWORD="<your password>"
echo -n $PASSWORD | gitops get bcrypt-hash | base64
```
