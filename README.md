# Walls of Excellence

<div align="center">

<img src="./docs/images/logo.png" alt="Logo" align="center" width="144px" height="144px"/>

## My home operations repository :octocat:

_... managed with Flux, Renovate and GitHub Actions_ 🤖

</div>

<div align="center">

[![License](https://img.shields.io/github/license/CowDogMoo/Walls-of-Excellence?label=License&style=flat&color=blue&logo=github)](https://github.com/lCowDogMoo/Walls-of-Excellence/blob/main/LICENSE)
[![Pre-Commit](https://github.com/CowDogMoo/Walls-of-Excellence/actions/workflows/pre-commit.yaml/badge.svg)](https://github.com/CowDogMoo/Walls-of-Excellence/actions/workflows/pre-commit.yaml)
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

- Flux

  If you're on a mac, run this:

  ```bash
  brew install fluxcd/tap/flux
  ```

  Otherwise, follow [these instructions](https://fluxcd.io/flux/installation/).

- Clone the repo:

  ```bash
  gh repo clone CowDogMoo/Walls-of-Excellence woe
  ```

- Bootstrap flux (if you haven't already, otherwise skip this step):

  ```bash
  export GITHUB_TOKEN=$FLUX_PAT
  export PATH_TO_FLUX_DEPLOYMENT=./kubernetes/flux-system/bootstrap-config
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

---

## Usage

- Reconcile flux resources:

  ```bash
  mage syncgitrepositories synchelmreleases synckustomizations
  ```

- Sync flux-system Kustomization resources with source:

  ```bash
  flux reconcile ks flux-system --with-source
  ```

- Sync cluster-apps Kustomization resources with source:

  ```bash
  flux reconcile ks cluster-apps --with-source -n flux-system
  ```

---

## Resources

This project was heavily influenced by the following:

- <https://github.com/onedr0p/home-ops/>
- <https://github.com/billimek/k8s-gitops>
