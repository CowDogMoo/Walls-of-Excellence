# Printer Monitor

A Kubernetes CronJob that monitors Brother printer health and attempts to wake
unresponsive printers.

## Overview

This service addresses a known issue with Brother MFC-L3770CDW printers that
become unresponsive after entering Deep Sleep mode, requiring manual reboots.
The monitor performs regular health checks and attempts to wake the printer
automatically.

## Features

- **Regular Health Checks**: Runs every 5 minutes via Kubernetes CronJob
- **Automatic Wake Attempts**: Attempts to wake printer if unresponsive
- **Belt Unit Error Detection**: Monitors for "No Belt Unit" errors
- **Secure Configuration**: Uses 1Password via External Secrets for credentials
- **Comprehensive Logging**: Detailed status information for troubleshooting

## Architecture

```text
┌─────────────────┐
│  Kubernetes     │
│  CronJob        │
│  (every 5 min)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────────┐
│  Python         │─────▶│  Brother Printer │
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
- **url**: Printer web interface URL

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

The container image is built in the
[warpgate](https://github.com/CowDogMoo/warpgate) repository:

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

## Resources

- [Brother MFC-L3770CDW Support](https://support.brother.com/g/b/producttop.aspx?c=us&lang=en&prod=mfcl3770cdw_us_eu_as)
- [External Secrets Operator](https://external-secrets.io/)
- [1Password Connect](https://developer.1password.com/docs/connect/)
