# Sliver C2

Begin by cloning the sliver repo locally and building the container image:

```bash
git clone https://github.com/BishopFox/sliver.git
cd $_
docker build --target production -t ghcr.io/metaredteam/purple-pirate/sliver .
```

Next, navigate to the cloned repo and build the container image locally

To push, you will need to create a classic personal access token by following
[these instructions](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry).

Once you have the token, assign the value to the GITHUB_TOKEN environment variable.

With that out of the way, you can build and push the container image to the
GitHub Container Registry:

```bash
echo $GITHUB_TOKEN | docker login ghcr.io -u metaredteam --password-stdin
docker push ghcr.io/metaredteam/purple-pirate/sliver
```

If everything worked, you should be able to pull the new container image
from GHC:

```bash
docker pull ghcr.io/metaredteam/purple-pirate/sliver:latest
```
