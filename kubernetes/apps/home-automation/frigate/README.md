# Frigate

NVR for the six wired cameras on VLAN 40. Pulls RTSP directly from the cameras;
Synology Surveillance Station is not in the path.

Runs on k8s9 (`node-role.kubernetes.io/storage=true`) — the only node with the
Rockchip BSP kernel (`6.1.0-1025-rockchip`) and the RK3588 media devices.

## Verified on hardware

| Check | Result |
| --- | --- |
| `h264_rkmpp` / `hevc_rkmpp` in image ffmpeg | present (ffmpeg 7.0) |
| RKNN runtime | `/usr/lib/librknnrt.so`, `rknnlite` imports |
| SoC autodetect | `rk3588` (requires privileged — see below) |
| Live 4K HEVC decode via `hevc_rkmpp` | 240 frames @ realtime |
| k8s9 → VLAN 40 RTSP | reachable, no firewall change needed |
| MetalLB `192.168.20.18` TCP+UDP on 8555 | assigned |

## Camera facts (measured, not assumed)

| Camera | IP | Main stream | Sub stream |
| --- | --- | --- | --- |
| front_left | .200 | HEVC 3840x2160 | HEVC 640x480 |
| front_right | .201 | assumed same as .200 | assumed same |
| back_left | .202 | assumed same as .200 | assumed same |
| back_right | .203 | HEVC 3840x2160 (via SS bridge) | not reachable |
| living_room | .204 | H.264 2560x1440 | **absent (404)** |
| garage | .205 | assumed same as .204 | assumed absent |

Hikvisions are HEVC (`preset-rk-h265`); Amcrests are H.264 (`preset-rk-h264`).
Setting one global hwaccel breaks half the fleet.

## Storage layout

| Path | Backing | Why |
| --- | --- | --- |
| `/config` | `local-path` on k8s9 NVMe | SQLite; corrupts over NFS |
| `/media/frigate` | `nfs-client` → Synology | recordings + snapshots |
| `/tmp/cache` | emptyDir on NVMe | segment staging before NFS move |
| `/dev/shm` | 512Mi tmpfs | 64MB default too small; Frigate wants ≥146MB |

## Pre-flight

### 1. Store the Surveillance Station RTSP credential

Back Right (192.168.40.203) is pulled through Surveillance Station's RTSP
restream rather than directly, because no password in the vault authenticates
to that camera — both `Back Right Camera` items
(`2bxl4dk7dzwf63lkkhfcpbets4`, `kajbbi33gkyhczluodyzmzidoa`) return HTTP 401,
while the other five return 200. SS still holds working credentials for it.

Retrieve the restream credential (stable across calls; re-check if SS is
reconfigured):

```sh
SID=$(curl -sk -G https://192.168.20.210:5001/webapi/entry.cgi \
  --data-urlencode api=SYNO.API.Auth --data-urlencode version=6 \
  --data-urlencode method=login --data-urlencode account=<dsm-user> \
  --data-urlencode passwd=<dsm-pass> --data-urlencode session=SurveillanceStation \
  --data-urlencode format=sid | jq -r .data.sid)
curl -sk -G https://192.168.20.210:5001/webapi/entry.cgi \
  --data-urlencode api=SYNO.SurveillanceStation.Camera --data-urlencode version=9 \
  --data-urlencode method=GetLiveViewPath --data-urlencode idList=12 \
  --data-urlencode _sid=$SID | jq -r '.data[].rtspPath'
```

Store the password portion in 1Password vault `automation` as item
`synology-surveillance-rtsp`, field `password`.

This bridge has real costs: it keeps Surveillance Station in the dependency
chain, routes 4K video through the NAS, and exposes only the main stream — so
Back Right decodes 3840x2160 for detection while its siblings decode 640x480.
The clean fix is a physical factory reset of that camera, after which it moves
to a direct pull like the others and gains a substream.

Camera IDs in Surveillance Station: front_left=9, front_right=10, back_left=11,
back_right=12, living_room=13, garage=14.

### 2. Raise the detect-stream resolution

Face recognition runs on the **detect** stream only. The Hikvision substreams
are 640x480, which yields roughly a 13-pixel-wide face at 10 ft — far below the
~80 px ArcFace needs. Raise each Hikvision substream to 1280x720 or 1920x1080 in
the camera web UI, then update `detect.width` / `detect.height` to match.

Object detection ("a person is there") works fine at 640x480. Only face
recognition is gated by this.

### 3. Enable the Amcrest substreams

`subtype=1` returns 404 on 192.168.40.204 — the substream is disabled. Until
it is enabled, those cameras decode their full 2560x1440 main stream for
detection, which is far more expensive than necessary. Enable the substream in
the Amcrest UI, add a `*_sub` go2rtc entry, and point the `detect` role at it.

### 4. Exclude Frigate recordings from HyperBackup

`/volume1` is a single 26.2 TB pool shared with the Immich library and its
pg_dump backups, which HyperBackup replicates to Backblaze B2.

DSM → HyperBackup → the B2 task → Edit source → deselect
`k8s/home-automation-frigate-media-*`.

Note the cameras are 4K/1440p, not 4MP: continuous recording across all six is
closer to 475 GB/day than the 250 GB/day originally estimated. The configured
retention (3d continuous / 14d motion / 30d alerts) keeps steady state near
1.5 TB.

### 5. Cap Frigate's share of the volume

`nfs-subdir-external-provisioner` ignores the `2Ti` PVC request — it only
creates a directory, so Frigate sees all free space on `/volume1`.

DSM → Control Panel → Shared Folder → the share backing `/volume1/k8s` →
Edit → Quota.

### 6. Verify the model block

`model.path: deci-fp16-yolonas_s` matches the plugin's
`^deci-fp16-yolonas_[sml]$` preset pattern, but the full download-and-convert
path has not been exercised end to end. Watch the first startup for conversion
errors. Note DeciAI's YOLO-NAS weights are non-commercial-use only.

## Why privileged

`frigate/detectors/plugins/rknn.py` calls `get_soc()`, which reads
`/proc/device-tree/compatible` — a symlink to `/sys/firmware/devicetree/base`.
containerd masks `/sys/firmware` with a read-only tmpfs, and that mask is
applied *after* volume mounts, so a hostPath cannot win. There is no config
option to supply the SoC directly.

A device plugin was tested and does solve device access
(`open(O_RDWR)` succeeds non-privileged on all five device nodes), but it does
not defeat the `/sys/firmware` mask, so it cannot replace privileged on its own.

Given Frigate parses untrusted video from network cameras, compensating
controls matter: keep VLAN 40 isolated, keep the cameras off the internet, and
pin the image tag rather than tracking `stable-rk`.

## Access

| Route | Address |
| --- | --- |
| Web UI | `https://frigate.techvomit.xyz` (Frigate's own auth on 8971) |
| RTSP restream | `rtsp://192.168.20.18:8554/<camera>` |
| WebRTC live view | `192.168.20.18:8555` TCP+UDP |

DNS comes from external-dns. The zone is publicly resolvable but points at
RFC1918 addresses, so remote access requires the UDM Pro VPN.

## Known trade-offs

- `config.yml` is mounted read-only from a ConfigMap, so git stays the source of
  truth. This disables the 0.17 camera wizard and the live zone/mask editor. To
  draw zones: temporarily remove the `config-file` mount, draw them in the UI,
  copy the coordinates back into the ConfigMap, restore the mount.
- No zones are defined yet. Alert quality depends almost entirely on them.
- `strategy: Recreate` is required. Two pods against one SQLite database
  corrupts it.
- `archiveOnDelete: "true"` on `nfs-client` means deleting the media PVC renames
  the directory rather than freeing the space.
