# Home Network (UniFi)

The cluster runs on a UniFi network: a UDM Pro gateway, USW switches, and
three U6 LR access points (Basement, Main Floor, Top Floor). This page covers
the VLAN layout, the cross-VLAN discovery settings that services in the cluster
depend on, and how to debug discovery when a device stops showing up.

## Networks

| Network | VLAN     | Subnet          | SSID                              |
| ------- | -------- | --------------- | --------------------------------- |
| Main    | untagged | 192.168.10.0/24 | `CowDogMoo`                       |
| Boss    | 20       | 192.168.20.0/24 | `CowDogMooBoss`                   |
| IoT     | 30       | 192.168.30.0/24 | `CowDogMooIoT`, `CowDogMooIoT-5G` |
| Camera  | 40       | 192.168.40.0/24 | none                              |
| Guest   | 49       | 192.168.50.0/24 | `CowDogMoo-Guest` (disabled)      |
| Dyson   | 60       | 192.168.60.0/24 | none                              |

- **Main:** phones, laptops, TVs. DHCP hands out AdGuard (192.168.20.17) as
  DNS.
- **Boss:** k8s nodes, Home Assistant, Apple TVs, trusted devices.
- **IoT:** Sonos amps (wired), Hue, ESPHome, the Chromecast.
- **Camera:** no internet access.
- **Dyson:** Dyson fans and purifiers only, assigned by per-client override.

Some clients are pinned to a VLAN that differs from the SSID they join, using
the per-client **Virtual Network Override** (client → Settings in the UI,
`virtual_network_override_id` in `rest/user`). The Chromecast joins
`CowDogMooBoss` but lands on IoT, and every Dyson joins `CowDogMooIoT` but
lands on Dyson.

## Cross-VLAN discovery (mDNS)

Phones on Main and Boss find the Sonos amps, Chromecast, and HomeKit
accessories on IoT through the gateway's mDNS proxy:

- **Settings → Networks → Gateway mDNS Proxy:** Custom
- **VLAN Scope:** Main, Boss, IoT, Camera
- **Service Scope:** All

The proxy re-sends each mDNS packet onto every other VLAN in scope, keeping
the original source IP, and also re-emits it from the gateway's own address on
each VLAN (`.10.1`, `.20.1`, `.30.1`, `.40.1`). That second copy echoes every
hostname probe straight back to the VLAN it came from, which is why the Dysons
live outside the scope (see below).

Things that look like they help but don't:

- **Service Scope → Specific** filters service types but still echoes hostname
  probes, with or without the default 25 services.
- Switching **Specific** back to **All** in the UI fails silently: the UI's
  `POST /proxy/network/api/s/default/set/setting/mdns` returns HTTP 400 while
  the service lists are still attached. Restore by POSTing the full setting
  body with `"mode": "all"` and empty `predefined_services` /
  `custom_services` to that same endpoint.
- `PUT rest/setting/mdns/<id>` returns `rc: ok` but ignores changes to
  `enabled_for_network_ids`. Change the VLAN scope in the UI.

### HomeKit

Home Assistant runs with `hostNetwork` pinned to k8s7 and its HomeKit Bridge
advertises `_hap._tcp` from 192.168.20.23:21063 on Boss. The Apple TV home
hubs are also on Boss, so the hub-to-bridge path needs no forwarding. iPhones
on Main reach the bridge only because Boss is in the mDNS scope.

## Multicast to Unicast is off on CowDogMooBoss

`CowDogMooBoss` has **Multicast to Unicast** disabled (WiFi → CowDogMooBoss →
Advanced, `mcastenhance_enabled: false`). Leave it off.

With it on, an AP only forwards a multicast group to the clients in its
driver's IGMP table. On the Top Floor AP the Boss entry for the mDNS group
(`01:00:5e:00:00:fb`, 224.0.0.251) became a `static` entry with one member and
stopped adding new ones. Phones joining Boss upstairs never got mDNS, so no
Sonos showed up in Spotify, while the same phone on `CowDogMoo` through the
same AP, or on Boss through the Basement AP, worked fine. Restarting the AP
did not fix it; disabling the setting did.

The other SSIDs still have it on. The controller shows it off for
`CowDogMooIoT`, but the APs apply `mcast.enhance=1` to that 2.4 GHz SSID
anyway; only `CowDogMooIoT-5G` really runs without it.

## Dyson VLAN

Dyson firmware (seen on E2B, K1M and K1N units) treats any copy of its own
mDNS hostname probe as a conflict, even when the data is identical, and starts
probing again. On a VLAN in the mDNS scope the proxy's echo arrives within
about 10 ms of every probe, so the unit probes every ~300 ms forever. It never
announces, its local MQTT port (1883) stays closed, and the loop and its echoes
flood every VLAN in scope with mDNS (most of the multicast on Boss while it
ran).

The fix is the Dyson VLAN, which is outside the mDNS scope. Nothing in the
cluster talks to the Dysons locally; the Dyson app goes through Dyson's cloud.

To add a new Dyson:

1. Set it up on `CowDogMooIoT` with the Dyson app as usual.
2. In UniFi, open the client → Settings → **Virtual Network Override** →
   `Dyson`. Turn off any fixed IP from the IoT range.
3. Reconnect the client. It should come back with a 192.168.60.x address.
4. Check it finished coming up: `nc -z 192.168.60.<n> 1883` should succeed.

## Debugging discovery

Start with the client side. If the device shows up on another SSID or another
AP, the phone's Local Network permission for the app is fine and the problem
is in the network path.

### From a host on the VLAN

`dns-sd -B _spotify-connect._tcp` on macOS shows mDNSResponder's cache, which
can hold entries long after delivery has stopped. For a fresh answer, send your
own query bound to port 5353 on the interface under test. A query from an
ephemeral port is a legacy unicast query, and responders answer it privately
instead of on the multicast group.

### On the access point

Enable **Settings → System → Advanced → Device SSH Authentication** with an
SSH key, then `ssh <user>@<ap-ip>`. The U6 LR runs BusyBox (`timeout -t 10
...`, not `timeout 10`) and has `tcpdump`.

| Interface             | Meaning                                         |
| --------------------- | ----------------------------------------------- |
| `br0`                 | Main bridge                                     |
| `br0.20`, `br0.30`, … | Per-VLAN bridges (`br0.60` once a Dyson is on)  |
| `ra0`, `ra1`, `ra2`   | 2.4 GHz SSIDs, in `/tmp/system.cfg` order       |
| `rai0`, `rai1`, …     | 5 GHz SSIDs                                     |

Useful checks:

```bash
# Which SSID is on which radio, and whether multicast to unicast is applied
grep -E 'wireless\.[0-9]+\.(devname|ssid|mcast\.enhance)=' /tmp/system.cfg

# mDNS reaching a VLAN and a radio
timeout -t 20 tcpdump -lni br0.20 udp port 5353
timeout -t 20 tcpdump -lni rai1 udp port 5353

# The driver's multicast-to-unicast IGMP table. bss_idx is per SSID; look for
# GrpId 01:00:5e:00:00:fb and check the phone's MAC is a member.
dmesg -c > /dev/null; iwpriv rai1 show igmpinfo; dmesg
```

`tcpdump` on a radio interface sees packets before the driver converts them
to unicast, so packets showing up there does not prove a given client receives
them. The IGMP table answers that.
