# evilginx2

## Description

Deploys evilginx2 in a k8s cluster.

## Requirements

Create a PAT and run the following command to create
a secret in the cluster:

```bash
USERNAME=l50 # Change me
PAT=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx # Change me
EMAIL=jayson.e.grace@gmail.com # Change me

kubectl create secret docker-registry ghcr-login-secret \
--docker-server=https://ghcr.io --docker-username=$USERNAME \
--docker-password=$PAT --docker-email=$EMAIL
```
