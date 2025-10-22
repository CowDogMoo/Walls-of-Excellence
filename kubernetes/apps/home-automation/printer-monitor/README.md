# Printer Monitor

A Kubernetes CronJob that monitors Brother printer health and attempts to wake unresponsive printers.

## Overview

This service addresses a known issue with Brother MFC-L3770CDW printers that become unresponsive after entering Deep Sleep mode, requiring manual reboots. The monitor performs regular health checks and attempts to wake the printer automatically.

## Features

- **Regular Health Checks**: Runs every 5 minutes via Kubernetes CronJob
- **Automatic Wake Attempts**: Attempts to wake printer if unresponsive
- **Belt Unit Error Detection**: Monitors for "No Belt Unit" errors
- **Secure Configuration**: Uses 1Password via External Secrets for credentials
- **Comprehensive Logging**: Detailed status information for troubleshooting

## Architecture

```
┌─────────────────┐
│  Kubernetes     │
│  CronJob        │
│  (every 5 min)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────────┐
│  Python         │─────▶│  Brother Printer │
│  Monitor Script │      │  192.168.30.120  │
└────────┬────────┘      └──────────────────┘
         │
         ▼
┌─────────────────┐
│  External       │
│  Secret         │
│  (1Password)    │
└─────────────────┘
```

## Configuration

### 1Password Setup

The monitor expects a 1Password item named **"Brother Printer"** with:

- **password**: Admin password for the printer
- **url**: Printer web interface URL (e.g., `http://192.168.30.120/`)

### Environment Variables

Configured via ConfigMap (`configmap.yaml`):

- `CHECK_INTERVAL`: Seconds between checks (default: 300)
- `TIMEOUT`: HTTP request timeout in seconds (default: 10)
- `MAX_RETRIES`: Maximum retry attempts (default: 3)
- `RUN_MODE`: Execution mode - `cronjob` or `continuous` (default: cronjob)

Configured via ExternalSecret (`externalsecret.yaml`):

- `PRINTER_URL`: Retrieved from 1Password
- `PRINTER_PASSWORD`: Retrieved from 1Password

## Deployment

### Prerequisites

1. 1Password Connect installed in cluster
2. `onepassword-connect` ClusterSecretStore configured
3. External Secrets Operator running

### Installation

1. Ensure the "Brother Printer" item exists in 1Password with password and URL fields

2. Deploy via Flux (automatic):

   ```bash
   flux reconcile ks cluster-apps --with-source -n flux-system
   ```

3. Or manually apply:

   ```bash
   kubectl apply -k kubernetes/apps/home-automation/printer-monitor/app
   ```

### Building the Container Image

The container image is built in the [warpgate](https://github.com/CowDogMoo/warpgate) repository:

```bash
cd ~/cowdogmoo/warpgate

# Setup buildx (one-time)
export BUILDX_NO_DEFAULT_ATTESTATIONS=1
docker buildx create --name mybuilder --bootstrap --use --driver docker-container

# Login to GHCR
echo $GITHUB_TOKEN | docker login ghcr.io -u YOUR_GITHUB_USER --password-stdin

# Build and push multi-arch image
docker buildx bake --file dockerfiles/printer-monitor/docker-bake.hcl \
  --push \
  --set "*.tags=ghcr.io/YOUR_GITHUB_USER/printer-monitor:latest"
```

See `~/cowdogmoo/warpgate/dockerfiles/printer-monitor/README.md` for details.

## Monitoring

### View CronJob Status

```bash
kubectl get cronjobs -n home-automation
```

### View Recent Jobs

```bash
kubectl get jobs -n home-automation -l app=printer-monitor
```

### View Logs

```bash
# Get latest job logs
kubectl logs -n home-automation -l app=printer-monitor --tail=100

# Follow logs in real-time
kubectl logs -n home-automation -l app=printer-monitor -f
```

### Trigger Manual Run

```bash
kubectl create job -n home-automation --from=cronjob/printer-monitor printer-monitor-manual-$(date +%s)
```

## Troubleshooting

### Common Issues

#### 1. Belt Unit Error

If logs show "⚠️  Belt Unit Error detected!":

1. Open printer top cover
2. Remove all drum/toner cartridges
3. Remove and firmly reseat the belt unit
4. Reinstall drums and toners
5. Close cover

#### 2. Printer Not Responding

If logs show "❌ Printer is not responding":

- Verify printer is powered on
- Check network connectivity: `ping 192.168.30.120`
- Verify printer IP hasn't changed
- May require physical power cycle

#### 3. ExternalSecret Not Syncing

```bash
kubectl get externalsecret -n home-automation printer-monitor-secret
kubectl describe externalsecret -n home-automation printer-monitor-secret
```

#### 4. Missing 1Password Item

Ensure the 1Password item exists and has the correct fields:

```bash
op item get "Brother Printer" --fields url,password
```

### Adjusting Check Frequency

Edit `configmap.yaml` and change the CronJob schedule in `cronjob.yaml`:

```yaml
# Every 5 minutes (default)
schedule: "*/5 * * * *"

# Every 10 minutes
schedule: "*/10 * * * *"

# Every hour
schedule: "0 * * * *"
```

## Known Issues

### Brother MFC-L3770CDW Deep Sleep Issue

- **Symptom**: Printer requires reboot after long idle periods
- **Root Cause**: Combination of Deep Sleep mode and intermittent Belt Unit sensor issue
- **Workaround**: This monitor helps, but hardware issue may require:
  1. Reseating belt unit
  2. Firmware update
  3. Contacting Brother support if under warranty

### Recommended Printer Settings

Via printer web interface (http://192.168.30.120/):

1. **Sleep Time**: Set to OFF or 240 minutes
2. **Auto Power Off**: Set to OFF or 8+ hours
3. **Deep Sleep**: Cannot be disabled (hardware limitation)

## Contributing

To extend the monitor:

1. Edit `monitor.py` to add new checks
2. Rebuild container image
3. Update CronJob to reference new image
4. Test with manual job trigger

## Resources

- [Brother MFC-L3770CDW Support](https://support.brother.com/g/b/producttop.aspx?c=us&lang=en&prod=mfcl3770cdw_us_eu_as)
- [External Secrets Operator](https://external-secrets.io/)
- [1Password Connect](https://developer.1password.com/docs/connect/)
