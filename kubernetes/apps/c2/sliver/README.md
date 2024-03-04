# Sliver C2

## Container Image Creation

Begin by cloning the sliver repo locally and building the container image:

```bash
git clone https://github.com/BishopFox/sliver.git
cd $_
docker build --target production -t ghcr.io/CowDogMoo/Walls-of-Excellence/sliver .
```

To push the resulting image, you will need to create a classic personal access
token by following [these instructions](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry).

Once you have the token, assign the value to the `GITHUB_TOKEN` environment variable.

With that out of the way, you can build and push the container image to the
GitHub Container Registry:

```bash
echo $GITHUB_TOKEN | docker login ghcr.io -u CowDogMoo --password-stdin
docker push ghcr.io/cowdogmoo/sliverc2
```

If everything worked, you should be able to pull the new container image
from GHC:

```bash
docker pull ghcr.io/cowdogmoo/sliverc2:latest
```
