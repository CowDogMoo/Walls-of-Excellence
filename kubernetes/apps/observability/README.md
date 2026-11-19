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

## Speaker activity

`sonos-events` (in `home-automation`) polls every Sonos group every two
seconds and prints one JSON line whenever a speaker starts, stops, changes
track or changes source. Alloy ships the lines to Loki as
`{job="sonos-events"}` with `room`, `event` and `source` labels, and Loki
keeps that stream for a year. The **Speaker Activity** dashboard in Grafana
reads it.

Why did the Family Room start playing:

```logql
{job="sonos-events", room="Family Room", event="playback_started"} | json
```

The `source` says what kind of controller started it: `spotify_connect` (a
Spotify app, from anywhere), `airplay`, `sonos_app_spotify`, `stream` (Music
Assistant or Home Assistant, with the serving host in `stream_host`), `tv`,
`line_in` or `radio`.

A speaker never learns which Spotify account is driving it. Any account that
has used a speaker over Spotify Connect while on the Wi-Fi keeps that speaker
in its device list and can start it from anywhere afterwards. To name the
person, find the first `spotify_connect` playback nobody in the house chose
and check which phone was on the Wi-Fi at that moment (the dashboard's bottom
panel).
