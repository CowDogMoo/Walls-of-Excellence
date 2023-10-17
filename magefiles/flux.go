package main

import (
	"bufio"
	"bytes"
	"fmt"
	"os/exec"
	"strings"
	"time"

	"github.com/fatih/color"
	"github.com/l50/goutils/v2/sys"
)

// syncResource triggers a sync of Flux resources (GitRepositories, Kustomizations, or HelmReleases) in a Kubernetes
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
// err := syncResource("gitrepositories", "GitRepositories synced successfully.")
//
//	if err != nil {
//	  log.Fatalf("Failed to sync resources: %v", err)
//	}
//
// log.Println("Resources synced successfully.")
func syncResource(resourceType, successMessage string) error {
	getCmd := exec.Command("kubectl", "get", resourceType, "--all-namespaces", "--no-headers")
	getOut, err := getCmd.Output()
	if err != nil {
		return fmt.Errorf("failed to run 'kubectl get': %w", err)
	}

	// Parse output of "kubectl get command"
	scanner := bufio.NewScanner(bytes.NewReader(getOut))
	for scanner.Scan() {
		line := scanner.Text()
		fields := strings.Fields(line)
		if len(fields) < 2 {
			continue // Skip invalid lines
		}
		namespace := fields[0]
		name := fields[1]

		// Run "kubectl annotate"
		annotateCmd := exec.Command("kubectl", "-n", namespace, "annotate",
			fmt.Sprintf("%s/%s", resourceType, name),
			fmt.Sprintf("reconcile.fluxcd.io/requestedAt=%d", time.Now().Unix()), "--overwrite")
		annotateOut, err := annotateCmd.CombinedOutput()
		if err != nil {
			return fmt.Errorf("failed to run 'kubectl annotate' for %s/%s: %w\n%s",
				namespace, name, err, string(annotateOut))
		}
	}

	fmt.Println(successMessage)

	return nil
}

// SyncGitRepositories triggers a sync of all Flux GitRepositories in a
// Kubernetes cluster by annotating them with
// the current timestamp. It runs a shell command that fetches all
// GitRepositories, parses their namespace and name,
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
	return syncResource("gitrepositories", "GitRepositories synced successfully.")
}

// SyncKustomizations triggers a sync of all Flux Kustomizations in a Kubernetes
// cluster by annotating them with the current timestamp. It runs a shell
// command that fetches all Kustomizations, parses their namespace and name,
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
	return syncResource("kustomizations", "Kustomizations synced successfully.")
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
	return syncResource("helmreleases", "HelmReleases synced successfully.")
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

	if _, err := sys.RunCommand("flux", "uninstall"); err != nil {
		return err
	}

	if err != nil {
		return fmt.Errorf(color.RedString(
			"failed to uninstall flux: %v", err))
	}

	return nil
}
