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

`sonos-events` (in `home-automation`) has every Sonos speaker push its
playback state to it and prints one JSON line whenever a group starts, stops,
changes track or changes source. Speakers close the connection after every
request, so polling them cost about a thousand connections a minute; pushes
cost none while the house is quiet. Every speaker is still polled once a
minute as a safety net, and one whose pushes stop arriving is logged as
`push_unavailable` and polled every two seconds until they return. Alloy
ships the lines to Loki as
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

## UniFi logs

Two streams hold what the gateway knows about clients and traffic.

`{source="unifi"}` is the gateway's syslog. It arrives at `vector-syslog` on
192.168.20.14 (UDP 514). The gateway is configured with that address, so the
Service pins it, and `UnifiSyslogSilent` fires when nothing has arrived for 30
minutes. Structured events have `event_type!="raw_syslog"`, and every key the
gateway sends becomes a JSON field: `client_mac`, `client_alias`,
`connected_to_device_name` and `wifi_rssi` on Wi-Fi events, and
`src_client_mac`, `dst`, `dpt`, `proto` and `policy_name` on firewall blocks.
The rest is device syslog from access points and switches, with the sender in
the `device` label and the daemon in `program`.

`{job="unifi-events"}` comes from `unifi-events`, which reads the controller's
flow and client-event APIs once a minute. Lines with `kind="flow"` are traffic
flows, both allowed and blocked, with the source MAC, both ports, the
destination domain and the firewall policy that matched. Lines with
`kind="client_event"` are connects, disconnects and roams. The controller
itself keeps only a few hours of flows, so this stream is the history.

Which devices talked to a speaker, and on which port:

```logql
{job="unifi-events", kind="flow"} | json | dst_ip="192.168.30.104"
  | line_format "{{.src_name}} {{.src_mac}} -> :{{.dst_port}} x{{.count}} ({{.policy}})"
```

Where a phone has been on the Wi-Fi:

```logql
{job="unifi-events", kind="client_event"} | json | client_mac="aa:bb:cc:dd:ee:ff"
```

A flow is recorded only when it crosses the gateway. A phone on the same
network as a speaker reaches it directly, and only the speaker's own log
(above) shows that. Repeats of one conversation within a poll are folded into
one line: `count` says how many there were and `last_time` when the newest
one started.
