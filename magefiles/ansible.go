package main

import (
	"fmt"
	"path/filepath"

	"github.com/fatih/color"
	"github.com/magefile/mage/sh"
)

// runAnsibleCommand is a helper function that runs ansible or ansible-playbook with provided arguments.
func runAnsibleCommand(command string, args ...string) error {
	if err := sh.RunV(command, args...); err != nil {
		return fmt.Errorf(color.RedString("failed to run %s: %v", command, err))
	}
	return nil
}

// AnsiblePing runs ansible all -m ping against all k8s nodes.
//
// Returns:
//
// error: An error if the ansible command fails.
//
// Example:
//
// err := AnsiblePing()
//
//	if err != nil {
//	  log.Fatalf("Ansible ping failed: %v", err)
//	}
//
// log.Println("Ansible ping successful.")
func AnsiblePing() error {
	args := []string{
		"all",
		"-m",
		"ping",
		"-i",
		"k3s-ansible/inventory/cowdogmoo/hosts.ini",
	}
	return runAnsibleCommand("ansible", args...)
}

// RunAnsible runs the ansible-playbook to provision the k8s nodes.
//
// Returns:
//
// error: An error if the ansible-playbook command fails.
//
// Example:
//
// err := RunAnsible()
//
//	if err != nil {
//	  log.Fatalf("Failed to run ansible playbook: %v", err)
//	}
//
// log.Println("Ansible playbook run successful.")
func RunAnsible() error {
	args := []string{
		filepath.Join("k3s-ansible", "site.yml"),
		"-i", filepath.Join("k3s-ansible", "inventory", "cowdogmoo", "hosts.ini"),
	}
	return runAnsibleCommand("ansible-playbook", args...)
}
