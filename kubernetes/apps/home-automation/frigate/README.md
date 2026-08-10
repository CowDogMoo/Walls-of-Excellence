# Frigate

NVR for the wired cameras on VLAN 40. Pulls RTSP directly from the cameras;
Synology Surveillance Station is not in the path.

Camera names, addresses, stream paths, and the whole `config.yml` body live in
1Password, not in this repo — see [Configuration](#configuration).

Runs on k8s9 (`node-role.kubernetes.io/storage=true`), the only node with the
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

The per-camera table — names, addresses, brands, measured main/sub stream
codecs and resolutions, and Surveillance Station camera IDs — is the
`FRIGATE_CAMERA_INVENTORY` field on the `frigate-config` 1Password item:

```sh
op item get frigate-config --vault automation \
  --fields label=FRIGATE_CAMERA_INVENTORY --format json | jq -r '.value'
```

The fleet is mixed: some cameras are HEVC (`preset-rk-h265`), others H.264
(`preset-rk-h264`). Setting one global hwaccel breaks half of them.

## Configuration

`config.yml` lives **entirely in 1Password**, in the `FRIGATE_CONFIG` field on
the `frigate-config` item (vault `automation`). ESO renders that field into a
Secret named `frigate-config` (via `externalsecret-config.yaml`), which the chart
mounts read-only at `/config/config.yml` through the `config-file` persistence
entry. Camera names, addresses, and stream paths never appear in git.

Camera RTSP credentials are inlined into that same field, so no camera name or
address appears in this repo at all. The per-camera 1Password items remain the
human record of each credential, but Frigate no longer reads them — **rotating a
camera password means updating both the camera's own item and `FRIGATE_CONFIG`.**

Only the MQTT credentials still arrive via `envFrom` as `{FRIGATE_MQTT_USER}` /
`{FRIGATE_MQTT_PASSWORD}` placeholders, sourced from `mosquitto-secret` by
`externalsecret.yaml`.

Because the field now holds live credentials, treat any local copy pulled for
editing as secret material and delete it when done.

To change the config:

1. Pull the current value:

   ```sh
   op item get frigate-config --vault automation \
     --fields label=FRIGATE_CONFIG --format json \
     | jq -r '.value' > /tmp/frigate-config.yml
   ```

2. Edit `/tmp/frigate-config.yml`, then validate it parses before pushing:

   ```sh
   yq -e '.cameras | keys' /tmp/frigate-config.yml
   ```

3. Push it back:

   ```sh
   op item edit frigate-config --vault automation \
     "FRIGATE_CONFIG[text]=$(cat /tmp/frigate-config.yml)"
   rm -f /tmp/frigate-config.yml
   ```

4. ESO refreshes the Secret on its interval (~1h). To expedite:

   ```sh
   kubectl -n home-automation annotate externalsecret frigate-config \
     force-sync=$(date +%s) --overwrite
   ```

   Reloader restarts the pod on the Secret change. Because `strategy: Recreate`
   is set, expect a short recording gap.

A bad config keeps Frigate crash-looping on a readOnly mount it cannot repair
itself — check `kubectl -n home-automation logs deploy/frigate` and fix the
1Password field, not the pod.

## Cloud cameras (Nest / Ring)

Two legacy Google Nest cams run through go2rtc's `nest:` source, but only
one is live. The garage cam has been physically offline for about a year
(its last HA motion event reads "Last year"), so its Frigate camera ships
`enabled: false`. SDM will still mint stream sessions for a camera that is
gone, those sessions 404 at the edge, and the dial churn rate-limits the
whole SDM account. Set it back to true when the camera has power and WiFi
again.

The cams are RTSP-only via the SDM API; they predate the 2021+ WebRTC
models, so their stream URLs carry `protocols=RTSP`. go2rtc calls
`GenerateRtspStream` and re-extends the 5-minute session token on its own.
Both nest cameras also carry an explicit `input_args` block instead of
`preset-rtsp-restream`. The flags are identical except for ffmpeg's
`-timeout`, raised from 10 s to 90 s: the session behind the restream can
need several DESCRIBE retries from go2rtc before it warms up, and the
preset's timeout expires first.

The SDM OAuth credentials (client id/secret, refresh token, Device Access
project id) are inlined into the config body in 1Password, the same as the
camera passwords. Env-var indirection through `externalsecret.yaml` was
tried first, and Flux reverted the uncommitted ExternalSecret, taking
go2rtc and every camera with it offline. The `nest-sdm` item in vault
`automation` is the human record of those credentials, copied from Home
Assistant's Nest integration. HA keeps using the same refresh token, since
Google refresh tokens are multi-use and non-rotating. Rotating them means
updating both `nest-sdm` and `FRIGATE_CONFIG`.

Stock go2rtc cannot start these streams at all. The Nest servers take
about 8 s to answer the first DESCRIBE after `GenerateRtspStream` (a warm
session answers in ~0.15 s), and go2rtc hardcodes a 5 s RTSP response
deadline, so every dial times out. Frigate's watchdog then retries in a
loop and burns the SDM `ExecuteDeviceCommand` rate limit. Sustained storms
push the Nest side into a penalized state where even fresh sessions answer
404 for a while, so kill the loop first
(`mosquitto_pub -t frigate/<cam>/enabled/set -m OFF`) and let it cool
before retrying. `/config` carries a patched go2rtc build that redials
until the session warms up
([go2rtc-nest-describe-retry.patch](go2rtc-nest-describe-retry.patch) on
v1.9.14). The Frigate image prefers `/config/go2rtc` over its bundled
1.9.10, so deleting the file falls back to stock. Rebuild with:

```sh
git clone --depth 1 --branch v1.9.14 https://github.com/AlexxIT/go2rtc
cd go2rtc && git apply .../go2rtc-nest-describe-retry.patch
CGO_ENABLED=0 GOOS=linux GOARCH=arm64 go build -ldflags "-s -w" -trimpath -o go2rtc .
kubectl cp go2rtc "home-automation/$(kubectl get pods -n home-automation \
  -l app.kubernetes.io/name=frigate -o name | cut -d/ -f2):/config/go2rtc"
```

The patched binary also brings the `ring:` source (added in 1.9.13, absent
from bundled 1.9.10).

Going through the cloud has a price. Video routes through Google's
servers, so the bandwidth gets spent twice. Streams drop and re-dial on
their own schedule. And revoking the Google OAuth grant takes out the
cameras in HA and Frigate at the same time.

The Ring doorbell gets a Frigate tile and event recording without the
battery cost. Frigate decodes every configured camera continuously, which
would flatten the doorbell battery, so the doorbell is split across two
cameras that share one on-demand go2rtc `ring:` stream.

The `front_door` camera is the dashboard tile. Its decode input is a
locally generated lavfi placeholder card (it needs
`/config/placeholder-font.ttf` on the PVC, currently Arial Bold), with
detect, record, and snapshots all off. Its live view maps to the go2rtc
stream instead: opening the camera dials Ring's cloud, closing it hangs
up, the same idle-until-viewed behavior as the HA card. The
`front_door` and `front_door_snapshot` streams are also reachable
through the restream endpoints in [Access](#access).

The `front_door_events` camera is how Ring events land in Review with
real detection and face recognition. It is hidden from the dashboard
(`ui.dashboard: false`) and consumes the same `ring:` stream, but with
detect and record on. Its baseline state is OFF via a retained message
on `frigate/front_door_events/enabled/set`; a Home Assistant automation
flips it ON for about two minutes whenever Ring pushes a motion or ding
event, then re-asserts the retained OFF. The camera still ships
`enabled: true` in the config because Frigate only honors the MQTT
toggle for cameras enabled there — the retained message, not the config
flag, is what keeps the doorbell out of the always-on pipeline.

Two details keep the short event window usable. `detect.width`/`.height`
are set explicitly (the stream is 1920x1080) so Frigate never dials the
doorbell at config load just to probe the resolution — that probe fires
on every restart and blocks startup about 30 s. And ffmpeg's `-timeout`
is raised to 90 s, because go2rtc's cold dial through Ring's cloud WebRTC
negotiation can outlast `preset-rtsp-restream`'s 10 s default right after
the camera is enabled, burning part of the window on retries.

The `ring:` source needs go2rtc ≥ 1.9.13, which the patched `/config`
binary provides. Its refresh token has to be separate from Home
Assistant's, because Ring issues tokens per client; the dedicated one
lives on the `ring-go2rtc` 1Password item and is inlined in the stream
URLs in `FRIGATE_CONFIG`. Ring also rotates that token on every
authentication, so the stored copy goes stale on its own. When
`front_door` dials start failing auth, regenerate with
`npx -p ring-client-api ring-auth-cli` and update the `ring-go2rtc` item
along with the URLs in `FRIGATE_CONFIG`. If that becomes a regular chore,
ring-mqtt persists rotated tokens and is the alternative.

## Storage layout

| Path | Backing | Why |
| --- | --- | --- |
| `/config` | `local-path` on k8s9 NVMe | SQLite; corrupts over NFS |
| `/media/frigate` | `nfs-client` → Synology | recordings + snapshots |
| `/tmp/cache` | emptyDir on NVMe | segment staging before NFS move |
| `/dev/shm` | 512Mi tmpfs | 64MB default too small; Frigate wants ≥146MB |

## Pre-flight

### 1. Store the Surveillance Station RTSP credential (retired)

**No longer in the path.** Back Right was originally pulled through
Surveillance Station's RTSP restream because no password in the vault
authenticated to it directly. A working password was later recovered, and the
config now pulls it directly like the rest. Kept here because the restream is
the fallback if that camera's credential is lost again.

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
  --data-urlencode method=GetLiveViewPath --data-urlencode idList=<ss-camera-id> \
  --data-urlencode _sid=$SID | jq -r '.data[].rtspPath'
```

Store the password portion in 1Password vault `automation` as item
`synology-surveillance-rtsp`, field `password`.

The bridge has real costs: it keeps Surveillance Station in the dependency
chain, routes 4K video through the NAS, and exposes only the main stream, so the
bridged camera decodes its full main stream for detection while its siblings
decode a substream. Per-camera Surveillance Station IDs are in the
`FRIGATE_CAMERA_INVENTORY` field on the `frigate-config` 1Password item.

### 2. Raise the detect-stream resolution

Face recognition runs on the **detect** stream only. The HEVC cameras' substreams
are 640x480, which yields roughly a 13-pixel-wide face at 10 ft, far below the
~80 px ArcFace needs. Raise each substream to 1280x720 or 1920x1080 in the camera
web UI, then update `detect.width` / `detect.height` to match.

Object detection ("a person is there") works fine at 640x480. Only face
recognition is gated by this.

### 3. Enable the H.264 cameras' substreams

`subtype=1` returns 404 on those cameras: the substream is disabled. Until it is
enabled, they decode their full 2560x1440 main stream for detection, which is far
more expensive than necessary. Enable the substream in the camera UI, add a
`*_sub` go2rtc entry, and point the `detect` role at it.

### 4. Exclude Frigate recordings from HyperBackup

`/volume1` is a single 26.2 TB pool shared with the Immich library and its
pg_dump backups, which HyperBackup replicates to Backblaze B2.

DSM → HyperBackup → the B2 task → Edit source → deselect
`k8s/home-automation-frigate-media-*`.

Note the cameras are 4K/1440p, not 4MP: continuous recording across the fleet is
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

- `config.yml` is mounted read-only from a Secret, so 1Password stays the source
  of truth. This disables the 0.17 camera wizard and the live zone/mask editor.
  To draw zones: temporarily remove the `config-file` mount, draw them in the UI,
  copy the coordinates back into 1Password, restore the mount.
- Config changes are invisible to `git diff` and to PR review — the repo holds
  only the ExternalSecret wrapper. That is the deliberate trade for keeping
  camera names, addresses, and stream paths out of a public repo.
- No zones are defined yet. Alert quality depends almost entirely on them.
- `strategy: Recreate` is required. Two pods against one SQLite database
  corrupts it.
- `archiveOnDelete: "true"` on `nfs-client` means deleting the media PVC renames
  the directory rather than freeing the space.
