#!/bin/bash
echo "Checking container images for multi-arch support (arm64 + amd64)..."
echo "================================================================"

# Get unique images first
kubectl get pods --all-namespaces -o jsonpath="{.items[*].spec.containers[*].image}" | tr -s '[:space:]' '\n' | sort | uniq | while read -r image; do
    [ -z "$image" ] && continue

    # Try to get architectures
    archs=$(docker manifest inspect "$image" 2> /dev/null | jq -r '.manifests[].platform.architecture' 2> /dev/null | sort | uniq | tr '\n' ',' | sed 's/,$//')

    if [ -z "$archs" ]; then
        echo "❓ UNKNOWN    | $image"
    elif [[ "$archs" == *"amd64"* ]] && [[ "$archs" == *"arm64"* ]]; then
        echo "✅ MULTI-ARCH | $image (supports: $archs)"
    elif [[ "$archs" == *"arm64"* ]] && [[ "$archs" != *"amd64"* ]]; then
        echo "⚠️  ARM-ONLY   | $image (supports: $archs)"
    elif [[ "$archs" == *"amd64"* ]] && [[ "$archs" != *"arm64"* ]]; then
        echo "⚠️  X86-ONLY   | $image (supports: $archs)"
    else
        echo "❔ OTHER      | $image (supports: $archs)"
    fi
done
