package main

import (
	"fmt"
	"os"
	"path/filepath"

	"github.com/fatih/color"
	goutils "github.com/l50/goutils"
	"github.com/magefile/mage/mg"
	"github.com/magefile/mage/sh"
)

func init() {
	os.Setenv("GO111MODULE", "on")
}

// InstallDeps Installs go dependencies
func InstallDeps() error {
	fmt.Println(color.YellowString("Installing dependencies."))

	if err := goutils.InstallGoPCDeps(); err != nil {
		return fmt.Errorf(color.RedString(
			"failed to install pre-commit dependencies: %v", err))
	}

	if err := goutils.InstallVSCodeModules(); err != nil {
		return fmt.Errorf(color.RedString(
			"failed to install vscode-go modules: %v", err))
	}

	return nil
}

// InstallPreCommitHooks Installs pre-commit hooks locally
func InstallPreCommitHooks() error {
	mg.Deps(InstallDeps)

	fmt.Println(color.YellowString("Installing pre-commit hooks."))
	if err := goutils.InstallPCHooks(); err != nil {
		return err
	}

	return nil
}

// RunPreCommit runs all pre-commit hooks locally
func RunPreCommit() error {
	mg.Deps(InstallDeps)

	fmt.Println(color.YellowString("Updating pre-commit hooks."))
	if err := goutils.UpdatePCHooks(); err != nil {
		return err
	}

	fmt.Println(color.YellowString(
		"Clearing the pre-commit cache to ensure we have a fresh start."))
	if err := goutils.ClearPCCache(); err != nil {
		return err
	}

	fmt.Println(color.YellowString("Running all pre-commit hooks locally."))
	if err := goutils.RunPCHooks(); err != nil {
		return err
	}

	return nil
}

// ApplyKubernetesResources applies the Kubernetes configuration defined in .yaml files and kustomization directories
// within the current directory and its subdirectories.
//
// It does the following:
// 1. For every directory, it checks for a kustomization.yaml file. If it exists, it runs 'kubectl apply -k .'
// 2. For every file named ks.yaml, it runs 'kubectl apply -f ks.yaml'
// 3. For every directory named 'app', it checks for a kustomization.yaml file. If it exists, it runs 'kubectl apply -k .'
//
// Returns:
//
// error: An error if any of the shell commands fail.
//
// Example:
//
//	if err := ApplyKubernetesResources(); err != nil {
//	  log.Fatalf("Failed to apply Kubernetes resources: %v", err)
//	}
func ApplyKubernetesResources() error {
	err := filepath.Walk(".", func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}

		if info.IsDir() {
			if err := processDirectory(path); err != nil {
				return err
			}
		} else if filepath.Base(path) == "ks.yaml" {
			if err := applyKubectl(path); err != nil {
				return err
			}
		}

		return nil
	})

	if err != nil {
		return fmt.Errorf("error walking the path: %w", err)
	}

	return nil
}

func processDirectory(dir string) error {
	kustomizationFile := filepath.Join(dir, "kustomization.yaml")
	if _, err := os.Stat(kustomizationFile); err == nil {
		if err := applyKustomize(dir); err != nil {
			return err
		}
	}

	return nil
}

func applyKustomize(dir string) error {
	fmt.Printf("Applying kustomize in directory: %s\n", dir)
	cmd := "kubectl"
	args := []string{"apply", "-k", "."}

	cwd, err := os.Getwd()
	if err != nil {
		return fmt.Errorf("error getting current working directory: %w", err)
	}

	if err := goutils.Cd(dir); err != nil {
		return fmt.Errorf("error changing directory: %w", err)
	}

	if err := sh.RunV(cmd, args...); err != nil {
		return fmt.Errorf("error applying kustomize: %w", err)
	}

	if err := goutils.Cd(cwd); err != nil {
		return fmt.Errorf("error changing directory: %w", err)
	}

	return nil
}

func applyKubectl(file string) error {
	cmd := "kubectl"
	args := []string{"apply", "-f", file}

	if err := sh.RunV(cmd, args...); err != nil {
		return fmt.Errorf("error applying kubectl: %w", err)
	}

	return nil
}
