# Developer Environment Setup

To get involved with this project,
[create a fork](https://docs.github.com/en/get-started/quickstart/fork-a-repo)
and follow along.

---

## Dependencies

- [Install homebrew](https://brew.sh/):

  ```bash
  # Linux
  sudo apt-get update
  sudo apt-get install -y build-essential procps curl file git
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"

  # macOS
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  ```

- [Install dependencies with brew](https://brew.sh/):

  ```bash
  brew install pre-commit kubectl kustomize
  brew install --cask flux
  ```

- [Install Mage](https://magefile.org/):

  ```bash
  go install github.com/magefile/mage@latest
  ```

- [Install Terragrunt](https://terragrunt.gruntwork.io/):

  ```bash
  brew install terragrunt
  ```

---

## Configure environment

1. Install pre-commit hooks:

   ```bash
   mage installPreCommitHooks
   ```

1. Update and run pre-commit hooks locally:

   ```bash
   mage runPreCommit
   ```

---

## Use self-hosted GH action runner

Change this value:

```yaml
runs-on: ubuntu-latest
```

to this:

```yaml
runs-on: self-hosted
```

---

## Destroy and Rebuild the Cluster

If the cluster becomes FUBAR, nuke it and rebuild:

```bash
# Destroy the cluster
mage runreset all

# Rebuild the cluster
mage runansible all
```
