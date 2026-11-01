# Observability

Useful link that serves as a guide for parsing UniFi Controller
logs: https://help.ui.com/hc/en-us/articles/33349041044119-UniFi-System-Logs-SIEM-Integration

## Kubernetes API audit log

Every control-plane node (k8s1, k8s2, k8s5) writes a kube-apiserver audit log
to `/var/log/kubernetes/audit/audit.log`: who created, changed or deleted
what, at Metadata level, with no reads and no request bodies. The policy and
rollout live in the `k3s-ansible` submodule (`k3s_audit_log_enabled`,
`audit-log.yml`).

The alloy DaemonSet ships it to Loki as `{job="k3s-audit"}` with `node` and
`verb` labels, dropping Flux server-side-apply dry runs on the way. A
single-replica `alloy-events` release ships Kubernetes events as
`{job="kubernetes-events"}`. Both are on the **Kubernetes API Audit** dashboard
in Grafana.

Who last touched a Deployment:

```logql
{job="k3s-audit"} | json user="user.username", ua="userAgent", resource="objectRef.resource", name="objectRef.name"
  | resource="deployments" | name="authentik-server"
```
