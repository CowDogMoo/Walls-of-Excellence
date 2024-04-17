#!/usr/bin/env bash

# pipefail sends error if any command fails in pipeline
set -eu -o pipefail

GODIR=$1 # the pre commit passes the matched file (go.mod) to us
GODIR=$(dirname "$GODIR")
pushd "$GODIR" > /dev/null
GOOS=windows go vet "./" 2>&1
GOOS=linux go vet "./" 2>&1
popd > /dev/null
