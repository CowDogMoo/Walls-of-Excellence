package main

import (
	"log"
	"os"
	"path/filepath"

	"context"
	"fmt"
	"sync"

	"github.com/bitfield/script"
	"github.com/fatih/color"
	goutils "github.com/l50/goutils"
	"github.com/magefile/mage/mg"
	"github.com/magefile/mage/sh"
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/tools/clientcmd"
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

// Sync applies the Kubernetes configuration defined in .yaml files and kustomization directories
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
//	if err := Sync(); err != nil {
//	  log.Fatalf("Failed to apply Kubernetes resources: %v", err)
//	}
func Sync() error {
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

// DestroyStuckNS fixes a namespace that is stuck terminating.
func DestroyStuckNS() error {
	home, err := os.UserHomeDir()
	if err != nil {
		return err
	}

	kubeconfig := filepath.Join(home, ".kube", "config")
	config, err := clientcmd.BuildConfigFromFlags("", kubeconfig)
	if err != nil {
		return err
	}

	clientset, err := kubernetes.NewForConfig(config)
	if err != nil {
		return err
	}

	var wg sync.WaitGroup
	namespacesClient := clientset.CoreV1().Namespaces()

	// list namespaces that are terminating
	nsList, err := namespacesClient.List(context.Background(), metav1.ListOptions{
		FieldSelector: "status.phase=Terminating",
	})
	if err != nil {
		return err
	}

	for _, ns := range nsList.Items {
		wg.Add(1)
		go func(ns corev1.Namespace) {
			defer wg.Done()

			// remove finalizers
			ns.ObjectMeta.Finalizers = []string{}
			_, err := namespacesClient.Update(context.Background(), &ns, metav1.UpdateOptions{})
			if err != nil {
				log.Fatal(err)
			}
		}(ns)
	}

	wg.Wait()

	return nil
}

// DestroyRancher is used to tear down a rancher deployment.
func DestroyRancher() error {
	rancherNS := "cattle-system"
	hackDir := "hack"
	goutils.Cd(hackDir)
	cmds := []string{
		// Delete webhook that breaks deployments when rancher fails to fully uninstall.
		"kubectl delete -n cattle-system MutatingWebhookConfiguration rancher.cattle.io",
		fmt.Sprintf("helm uninstall rancher -n %s", rancherNS),
		// Install dependency required for rancher_cleanup.py
		"python3 -m pip install kubernetes",
		"python3 rancher_cleanup.py",
		// delete apiservice that can get stuck due to no backend
		// https://github.com/helm/helm/issues/6361#issuecomment-538220109
		"kubectl delete apiservices v1beta1.metrics.k8s.io",
		"kubectl delete ns cattle-fleet-system",
		"kubectl delete mutatingwebhookconfigurations.admissionregistration.k8s.io --ignore-not-found=true rancher.cattle.io",
		"kubectl delete ns cattle-fleet-system",
		"kubectl delete ns cattle-fleet-local-system",
		"kubectl delete ns cattle-fleet-clusters-system",
		"kubectl delete ns cattle-fleet-system",
		"kubectl delete ns cattle-global-nt",
		"kubectl delete ns cattle-impersonation-system",
		"kubectl delete ns cattle-global-data",
		"kubectl delete mutatingwebhookconfigurations.admissionregistration.k8s.io rancher.cattle.io",
		"kubectl delete clusters.provisioning.cattle.io -n fleet-local local",
		fmt.Sprintf("kubectl delete ns %s", rancherNS),
	}

	for _, cmd := range cmds {
		if _, err := script.Exec(cmd).Stdout(); err != nil {
			if err != nil {
				fmt.Println(err.Error())
			}
		}
	}

	if err := DestroyStuckNS(); err != nil {
		return err
	}

	return nil
}
