# Walls of Excellence

<div align="center">

<img src="https://camo.githubusercontent.com/5b298bf6b0596795602bd771c5bddbb963e83e0f/68747470733a2f2f692e696d6775722e636f6d2f7031527a586a512e706e67" align="center" width="144px" height="144px"/>

### My home operations repository :octocat:

_... managed with Flux, Renovate and GitHub Actions_ 🤖

</div>

<div align="center">

[![Renovate](https://github.com/CowDogMoo/Walls-of-Excellence/actions/workflows/renovate.yaml/badge.svg)](https://github.com/CowDogMoo/Walls-of-Excellence/actions/workflows/renovate.yaml)

</div>

---

## 📖 Overview

Walls of Excellence (woe) is a mono repository for my home
infrastructure and Kubernetes cluster which adheres to
Infrastructure as Code (IaC) and GitOps practices where possible

---

## Table of Contents

- [Developer Environment Setup](docs/dev.md)
- [Installation](#installation)

---

## Installation

- Clone the repo:

  ```bash
  gh repo clone CowDogMoo/Walls-of-Excellence woe
  ```

- Bootstrap flux:

  ```bash
  export GITHUB_TOKEN=$FLUX_PAT_GOES_HERE
  export PATH_TO_FLUX_DEPLOYMENT=./kubernetes/flux-system/config
  export REPO_OWNER=CowDogMoo
  export REPO_NAME=Walls-of-Excellence

  flux bootstrap github \
  --owner=$REPO_OWNER \
  --repository=$REPO_NAME \
  --path=$PATH_TO_FLUX_DEPLOYMENT \
  --personal \
  --token-auth
  ```

- Build cloud resources:

  ```bash
  mage apply
  ```

- Reconcile flux resources:

  ```bash
  flux reconcile kustomization flux-system
  ```

---

## Resources

This project was heavily influenced by the following:

- <https://github.com/onedr0p/home-ops/>
- <https://github.com/billimek/k8s-gitops>
