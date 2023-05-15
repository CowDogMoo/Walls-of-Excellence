# Rancher

This requires a super jenky fix to get rancher to
work with the latest version of k3s:

1. Download and extract the latest chart:

   ```bash
   cd kubernetes/apps/rancher/rancher/app
   helm pull rancher-latest/rancher
   tar -zxvf rancher-*.tgz
   ```

1. Get the current version of k3s:

   ```bash
   kgn | awk -F ' ' '{print $5}' | uniq | grep -v VERSION
   ```

1. Set the output of that command to the `kubeVersion` value in `Chart.yaml`.
   For example:

   ```yaml
   kubeVersion: < v1.26.1+k3s1
   ```

1. Repackage the chart:

   ```bash
   helm package rancher
   ```

1. Move it into place:

   ```bash
   mv rancher-*.tgz charts
   ```

1. Update the chart value in helmrelease to match the new version

   For example, if the latest version is 2.7.3:

   ```yaml
   chart: ./charts/rancher-2.7.3
   ```

Resources:\*\*

- <https://forums.rancher.com/t/installation-failed-chart-requires-kubeversion-1-25-0-0-which-is-incompatible-with-kubernetes-v1-26-0/39738>
