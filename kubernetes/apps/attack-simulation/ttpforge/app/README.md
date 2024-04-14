# TTPForge

TTPForge is a Cybersecurity Framework for developing, automating, and executing
attacker Tactics, Techniques, and Procedures (TTPs).

## Using TTPForge in k8s

1. Get a shell to the `ttpforge` pod:

   ```bash
   kubectl exec -it -n attack-simulation deployments/ttpforge -- bash
   ```

1. Run a test:

   ```bash
   ttpforge run forgearmory//discovery-and-collection/discover-writable-directories/discover-writable-directories.yaml
   ```
