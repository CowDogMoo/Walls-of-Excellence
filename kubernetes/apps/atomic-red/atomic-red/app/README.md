# Atomic Red Team

Atomic Red Team (ART) is a library of TTPs that can be executed to
validate security controls and test detection capabilities.

## Using Atomic Red Team in k8s

1. Get a shell to the `atomic-red` pod:

   ```bash
   kubectl exec -it -n atomic-red deployments/atomic-red -- pwsh
   ```

1. Import the `Invoke-AtomicRedTeam` module and set the default parameter
   values:

   ```powershell
   Import-Module "~/AtomicRedTeam/invoke-atomicredteam/Invoke-AtomicRedTeam.psd1" -Force
   ```

1. Run a test:

   ```powershell
   Invoke-AtomicTest T1070.004 -ShowDetails
   ```
