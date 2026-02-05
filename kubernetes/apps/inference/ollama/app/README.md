# Ollama

A Kubernetes deployment of Ollama for local model inference with persistent
model storage and an optional pre-download job.

## Overview

This deployment runs the `ollama/ollama` container with a persistent volume for
model storage. A one-shot Job can be used to pre-pull models into the shared
volume so the main deployment starts serving immediately.

## Features

- **Single-Replica Inference**: Simple, stable deployment for local inference
- **Persistent Models**: Models stored on a PVC at `/root/.ollama`
- **Pre-Download Job**: Optional Job to pull models ahead of time
- **Ingress**: External access via Traefik
- **Resource Limits**: CPU/memory requests and limits set for reliability

## Architecture

```text
┌──────────────────────────────────────────────────────┐
│  Ollama Deployment                                   │
│                                                      │
│  ┌────────────────────┐                              │
│  │  ollama container  │                              │
│  │  (HTTP :11434)     │                              │
│  └─────────┬──────────┘                              │
│            │                                         │
└────────────┼─────────────────────────────────────────┘
             │
             ▼
      ┌─────────────┐
      │  PVC        │
      │  /root/.ollama
      └─────────────┘
             ▲
             │
┌────────────┴─────────────────────────────────────────┐
│  model-download Job (optional)                        │
│  pulls models into the PVC                             │
└──────────────────────────────────────────────────────┘
```

## Configuration

### Namespace

All resources are deployed to the `inference` namespace via Kustomize.

### Ingress

- **Host**: `ollama.techvomit.xyz`
- **Port**: `11434`
- **Ingress Class**: `ingress-traefik`

### Storage

- **PVC**: `ollama-models`
- **Size**: `50Gi`
- **StorageClass**: `local-path`
- **Mount**: `/root/.ollama`

### Resources

- **Requests**: 1 CPU, 8Gi memory
- **Limits**: 6 CPU, 16Gi memory

## Models

### Preloaded model(s)

The download Job currently pulls:

- `qwen2.5-coder:7b-instruct`

To add more models, edit `model-download-job.yaml` and append additional
`ollama pull` commands.

## Deployment

### Install via Flux

```bash
flux reconcile ks cluster-apps --with-source -n flux-system
```

### Apply manually

```bash
kubectl apply -f kubernetes/apps/inference/ollama/app/
```

## Operations

### Check status

```bash
kubectl get pods -n inference -l app.kubernetes.io/name=ollama
```

### View logs

```bash
kubectl logs -n inference -l app.kubernetes.io/name=ollama -c ollama
```

### Verify service

```bash
kubectl get svc -n inference ollama
```

### Test the API

```bash
curl http://ollama.techvomit.xyz:11434/api/tags
```

## Model Management

### Run the pre-download job

```bash
kubectl apply -n inference -f kubernetes/apps/inference/ollama/app/model-download-job.yaml
```

### Add another model

1. Edit `model-download-job.yaml` and add more `ollama pull` lines
2. Re-apply the job

Example:

```sh
ollama pull qwen2.5-coder:7b-instruct
ollama pull <model>:<tag>
```

## Troubleshooting

### Pod won’t start

```bash
kubectl describe pod -n inference -l app.kubernetes.io/name=ollama
```

### Model download job failing

```bash
kubectl logs -n inference job/model-download
```

### No models found

```bash
kubectl exec -n inference deploy/ollama -- ls -la /root/.ollama
```
