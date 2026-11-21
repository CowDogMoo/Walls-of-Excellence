# Rollout: kured, CoreDNS HA and leader-election tuning

This change follows up on the 2026-11-17 outage. It deploys kured to
coordinate node reboots, runs two CoreDNS replicas on separate nodes, and
lengthens the Flux and cert-manager leader-election durations.

Two follow-ups happen outside this repo. The companion k3s-ansible PR handles
the host side: it turns off `Unattended-Upgrade::Automatic-Reboot` and keeps
the DHCP nodes (k8s1, k8s2, k8s6, k8s9) from dropping their address on a link
flap. Moving k8s2's etcd/root disk to an SSD is a hardware job. This repo's
`k3s-ansible` submodule pointer stays where it is.

## Order

Do both steps in one session, in this order:

1. Run the k3s-ansible change on every node. Check that automatic reboots are
   off before going on:

   ```bash
   apt-config dump | grep Automatic-Reboot   # expect "false"
   ```

2. Merge this PR. Flux deploys kured, and kured handles reboots from then on.

Doing the host change first leaves a gap of a few hours where nothing reboots
nodes. That's harmless. The other order isn't: if kured runs while
unattended-upgrades can still reboot nodes at 03:00, kured could be draining
one etcd member while unattended-upgrades reboots another, with no lock
between them.

## k3s upgrades and kured reboots

kured's lock only covers kured. system-upgrade-controller restarts k3s on
every node when a k3s update lands, and it doesn't take that lock. A k3s
upgrade on one control-plane node at the same time as a kured reboot on
another would leave etcd without quorum.

To keep them apart, Renovate merges `k3s-io/k3s` and system-upgrade-controller
updates only between 09:00 and 14:00 America/Denver (the `automergeSchedule`
rule in `.github/renovate.json5`). kured reboots only between 02:00 and 05:00.
Platform automerge is off for these updates, because GitHub would merge as
soon as checks pass, whatever the time. Merge any manual k3s bump in daytime
too.

## Checks after the merge

```bash
kubectl -n system-upgrade rollout status ds/kured
kubectl -n kube-system get hpa coredns
kubectl -n kube-system get pods -l k8s-app=kube-dns -o wide   # two pods, two nodes
```
