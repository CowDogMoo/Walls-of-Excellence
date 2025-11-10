#!/usr/bin/env bash
set -euo pipefail

# Script to add volume mounts and volume definitions to guacamole deployment
# Usage: add-connection-volumes.sh <deployment-file> <connection-name> <secret-name>

DEPLOYMENT_FILE="${1:-}"
CONNECTION_NAME="${2:-}"
SECRET_NAME="${3:-}"

if [ -z "$DEPLOYMENT_FILE" ] || [ -z "$CONNECTION_NAME" ] || [ -z "$SECRET_NAME" ]; then
    echo "Usage: $0 <deployment-file> <connection-name> <secret-name>"
    exit 1
fi

if [ ! -f "$DEPLOYMENT_FILE" ]; then
    echo "Error: Deployment file not found: $DEPLOYMENT_FILE"
    exit 1
fi

# Check if volume mount already exists
if ! grep -q "/connections/$CONNECTION_NAME" "$DEPLOYMENT_FILE"; then
    echo "Adding volume mount to deployment..."

    # Find the line with the last connection mount
    LAST_CONN_MOUNT=$(grep -n "mountPath: /connections/" "$DEPLOYMENT_FILE" | tail -1 | cut -d: -f1)

    if [ -n "$LAST_CONN_MOUNT" ]; then
        # Add after the readOnly line of the last connection (2 lines after mountPath)
        READONLY_LINE=$((LAST_CONN_MOUNT + 2))

        # Create temp file with the new lines inserted
        awk -v line="$READONLY_LINE" -v conn="$CONNECTION_NAME" '
      NR == line {
        print
        print "            - mountPath: /connections/" conn
        print "              name: connection-" conn
        print "              readOnly: true"
        next
      }
      { print }
    ' "$DEPLOYMENT_FILE" > "$DEPLOYMENT_FILE.tmp" && mv "$DEPLOYMENT_FILE.tmp" "$DEPLOYMENT_FILE"

        echo "✅ Added volume mount to deployment"
    else
        echo "⚠️  No existing connection mounts found, skipping volume mount"
    fi
fi

# Add volume definition (check in volumes section specifically, not volumeMounts)
if ! grep -q "^        - name: connection-$CONNECTION_NAME" "$DEPLOYMENT_FILE"; then
    echo "Adding volume definition to deployment..."

    # Find the last connection volume (with 8-space indentation in volumes section)
    LAST_VOL=$(grep -n "^        - name: connection-" "$DEPLOYMENT_FILE" | tail -1 | cut -d: -f1)

    if [ -n "$LAST_VOL" ]; then
        # Find the secretName line (2 lines after the volume name)
        SECRET_LINE=$((LAST_VOL + 2))

        # Create temp file with the new lines inserted
        awk -v line="$SECRET_LINE" -v conn="$CONNECTION_NAME" -v secret="$SECRET_NAME" '
      NR == line {
        print
        print "        - name: connection-" conn
        print "          secret:"
        print "            secretName: " secret
        next
      }
      { print }
    ' "$DEPLOYMENT_FILE" > "$DEPLOYMENT_FILE.tmp" && mv "$DEPLOYMENT_FILE.tmp" "$DEPLOYMENT_FILE"

        echo "✅ Added volume definition to deployment"
    else
        echo "⚠️  No existing connection volumes found, skipping volume definition"
    fi
fi
