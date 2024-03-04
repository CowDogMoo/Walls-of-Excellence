# Atomic Red Team

## Container Image Creation

To push the container image to the GitHub Container Registry (GHCR), you will
need to create a classic personal access token by following

Begin by cloning the sliver repo locally and building the container image:

```bash
git clone https://github.com/redcanaryco/invoke-atomicredteam.git
cd invoke-atomicredteam/docker
```

To push the container image to the `GitHub Container Registry` (`GHCR`), you
will need to create a classic personal access token by following
[these instructions](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry).

Once you have the token, assign the value to the `GITHUB_TOKEN` environment variable.

With that out of the way, you can build and push the container image to `GHCR`:

```bash
echo $GITHUB_TOKEN | docker login ghcr.io -u cowdogmoo --password-stdin
docker buildx build --platform linux/amd64,linux/arm64,linux/arm/v7 -t ghcr.io/cowdogmoo/atomic-red:latest --push .
```

If everything worked, you should now be able to pull the new container image
from `GHCR`:

```bash
docker pull ghcr.io/cowdogmoo/atomic-red:latest
```
