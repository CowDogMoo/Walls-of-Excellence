# Walls of Excellence

<div align="center">

<img src="https://camo.githubusercontent.com/5b298bf6b0596795602bd771c5bddbb963e83e0f/68747470733a2f2f692e696d6775722e636f6d2f7031527a586a512e706e67" align="center" width="144px" height="144px"/>

### My home operations repository :octocat:

_... managed with Flux, Renovate and GitHub Actions_ 🤖

</div>

---

## 📖 Overview

Walls of Excellence (woe) is a mono repository for my home infrastructure and Kubernetes cluster
which adheres to Infrastructure as Code (IaC) and GitOps practices where possible

---

## Table of Contents

- [Developer Environment Setup](docs/dev.md)
- [Installation](#installation)

---

## Installation

- Bootstrap flux:

  ```bash
  export GITHUB_TOKEN=$FLUX_PAT_GOES_HERE
  export PATH_TO_FLUX_DEPLOYMENT=./kubernetes/flux-system/config
  export REPO_OWNER=CowDogMoo
  export REPO_NAME=walls-of-excellence

  flux bootstrap github \
  --owner=$REPO_OWNER \
  --repository=$REPO_NAME \
  --path=$PATH_TO_FLUX_DEPLOYMENT \
  --personal \
  --token-auth
  ```
