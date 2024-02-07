#!/bin/bash
set -ex

CRD=$1
RELEASE_NAME=cert-manager
RELEASE_NS=cert-manager

kubectl annotate crd "$CRD"= meta.helm.sh/release-name=$RELEASE_NAME --overwrite
kubectl annotate crd "$CRD" meta.helm.sh/release-namespace=$RELEASE_NS --overwrite
kubectl label crd "$CRD" app.kubernetes.io/managed-by=Helm --overwrite
