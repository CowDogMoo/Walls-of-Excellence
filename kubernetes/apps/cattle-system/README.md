# Rancher

Runs [Rancher](https://artifacthub.io/packages/helm/rancher-stable/rancher).

## Ensure default admin has a password

```bash
kubectl --kubeconfig $KUBECONFIG -n cattle-system exec $(kubectl --kubeconfig $KUBECONFIG -n cattle-system get pods -l app=rancher | grep '1/1' | head -1 | awk '{ print $1 }') -- ensure-default-admin
```

**Resource:** <https://github.com/rancher/rancher/issues/30243>

## Reset password

```bash
kubectl -n cattle-system exec $(kubectl  -n cattle-system get pods -l app=rancher | grep '1/1' | head -1 | awk '{ print $1 }') -- reset-password
```
