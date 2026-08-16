#!/usr/bin/env bash
# serve-static.sh — put an arbitrary local HTML file on the cluster, briefly.
#
#   ./serve-static.sh up   gift-board ~/Downloads/gift-board.html gift-board.techvomit.xyz
#   ./serve-static.sh down gift-board
#   ./serve-static.sh list
#
# The content never enters git. Only this script and the template do.
set -euo pipefail

TEMPLATE="${TEMPLATE:-$(dirname "$0")/static-site.tmpl.yaml}"
# Wildcard *.techvomit.xyz cert, auto-reflected into new namespaces by reflector.
TLS_SECRET="${TLS_SECRET:-techvomit-xyz-production-tls}"

usage() {
    sed -n '2,8p' "$0" | sed 's/^# \{0,1\}//'
    exit 1
}

up() {
    local name="$1" file="$2" host="$3"
    [[ -f "$file" ]] || {
        echo "no such file: $file" >&2
        exit 1
    }
    [[ "$host" == *.techvomit.xyz ]] \
        || echo "warning: ${host} is not covered by the ${TLS_SECRET} wildcard cert" >&2

    export NAME="$name" HOST="$host" TLS_SECRET
    export CONTENT_HASH
    CONTENT_HASH="$(sha256sum "$file" | cut -c1-16)"

    # namespace + workload first, so the ConfigMap has somewhere to land
    # shellcheck disable=SC2016  # literal list tells envsubst which vars to touch
    envsubst '${NAME} ${HOST} ${TLS_SECRET} ${CONTENT_HASH}' < "$TEMPLATE" \
        | kubectl apply -f -

    # server-side apply: content can exceed the 256KB last-applied-configuration
    # annotation cap that client-side apply hits on large files
    kubectl -n "$name" create configmap "${name}-content" \
        --from-file=index.html="$file" \
        --dry-run=client -o yaml \
        | kubectl apply --server-side --force-conflicts -f -

    kubectl -n "$name" rollout restart deploy/"$name" > /dev/null
    kubectl -n "$name" rollout status deploy/"$name" --timeout=90s

    echo
    echo "  https://${host}"
    echo "  tear down:  $0 down ${name}"
}

down() {
    local name="$1"
    kubectl get ns "$name" -o jsonpath='{.metadata.labels.serve-static/ephemeral}' 2> /dev/null \
        | grep -q true || {
        echo "'$name' isn't a serve-static namespace — refusing" >&2
        exit 1
    }
    kubectl delete ns "$name" --wait=false
    echo "deleting namespace ${name}"
}

list() {
    kubectl get ns -l serve-static/ephemeral=true \
        -o custom-columns=NAME:.metadata.name,AGE:.metadata.creationTimestamp
}

case "${1:-}" in
    up)
        [[ $# -eq 4 ]] || usage
        up "$2" "$3" "$4"
        ;;
    down)
        [[ $# -eq 2 ]] || usage
        down "$2"
        ;;
    list) list ;;
    *) usage ;;
esac
