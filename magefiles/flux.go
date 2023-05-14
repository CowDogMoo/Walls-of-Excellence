package main

import (
	"bytes"
	"fmt"
	"os/exec"

	"github.com/fatih/color"
	"github.com/magefile/mage/sh"
)

// SyncResource triggers a sync of Flux resources (GitRepositories, Kustomizations, or HelmReleases) in a Kubernetes
// cluster by annotating them with the current timestamp. It runs a shell command that fetches all resources of the
// specified type, parses their namespace and name, and annotates each of them. If the command fails, an error is returned.
//
// Parameters:
//
// resourceType: A string representing the type of the resource to sync (GitRepositories, Kustomizations, or HelmReleases).
// successMessage: A string representing the message to print upon successful sync.
//
// Returns:
//
// error: An error if the shell command fails.
//
// Example:
//
// err := SyncResource("gitrepositories", "GitRepositories synced successfully.")
//
//	if err != nil {
//	  log.Fatalf("Failed to sync resources: %v", err)
//	}
//
// log.Println("Resources synced successfully.")
func SyncResource(resourceType, successMessage string) error {
	cmd := exec.Command("bash", "-c", fmt.Sprintf(`kubectl get %s --all-namespaces --no-headers | awk '{print $1, $2}' | xargs -I{} bash -c 'kubectl -n {} annotate %s/{} reconcile.fluxcd.io/requestedAt=$(date +%%s) --overwrite'`, resourceType, resourceType))

	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	err := cmd.Run()

	fmt.Println("STDOUT:", stdout.String())
	fmt.Println("STDERR:", stderr.String())

	if err != nil {
		return err
	}

	if stderr.String() == "" {
		fmt.Println(successMessage)
	}

	return nil
}

// SyncGitRepositories triggers a sync of all Flux GitRepositories in a Kubernetes cluster by annotating them with
// the current timestamp. It runs a shell command that fetches all GitRepositories, parses their namespace and name,
// and annotates each of them. If the command fails, an error is returned.
//
// Returns:
//
// error: An error if the shell command fails.
//
// Example:
//
// err := SyncGitRepositories()
//
//	if err != nil {
//	  log.Fatalf("Failed to sync GitRepositories: %v", err)
//	}
//
// log.Println("GitRepositories synced successfully.")
func SyncGitRepositories() error {
	return SyncResource("gitrepositories", "GitRepositories synced successfully.")
}

// SyncKustomizations triggers a sync of all Flux Kustomizations in a Kubernetes cluster by annotating them with
// the current timestamp. It runs a shell command that fetches all Kustomizations, parses their namespace and name,
// and annotates each of them. If the command fails, an error is returned.
//
// Returns:
//
// error: An error if the shell command fails.
//
// Example:
//
// err := SyncKustomizations()
//
//	if err != nil {
//	  log.Fatalf("Failed to sync Kustomizations: %v", err)
//	}
//
// log.Println("Kustomizations synced successfully.")
func SyncKustomizations() error {
	return SyncResource("kustomizations", "Kustomizations synced successfully.")
}

// SyncHelmReleases triggers a sync of all Flux HelmReleases in a Kubernetes cluster by annotating them with
// the current timestamp. It runs a shell command that fetches all HelmReleases, parses their namespace and name,
// and annotates each of them. If the command fails, an error is returned.
//
// Returns:
//
// error: An error if the shell command fails.
//
// Example:
//
// err := SyncHelmReleases()
//
//	if err != nil {
//	  log.Fatalf("Failed to sync HelmReleases: %v", err)
//	}
//
// log.Println("HelmReleases synced successfully.")
func SyncHelmReleases() error {
	return SyncResource("helmreleases", "HelmReleases synced successfully.")
}

// UninstallFlux uninstalls FluxCD from the Kubernetes cluster by
// running the 'flux uninstall' command. If the command
// fails, an error is returned.
//
// Returns:
//
// error: An error if the 'flux uninstall' command fails.
//
// Example:
//
// err := UninstallFlux()
//
//	if err != nil {
//	  log.Fatalf("Failed to uninstall Flux: %v", err)
//	}
//
// log.Println("Flux uninstalled successfully.")
func UninstallFlux() error {
	var err error

	fmt.Println(color.GreenString(
		"Uninstalling flux, please wait.\n"))

	if err := sh.RunV("flux", "uninstall"); err != nil {
		return err
	}

	if err != nil {
		return fmt.Errorf(color.RedString(
			"failed to apply TF modules: %v", err))
	}

	return nil

}
