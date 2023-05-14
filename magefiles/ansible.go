package main

import (
	"fmt"
	"path/filepath"

	"github.com/fatih/color"
	"github.com/magefile/mage/sh"
)

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

// RunReset executes the 'ansible-playbook' command with the 'reset.yml' playbook on the master or node or all,
// based on the provided group.
//
// Parameters:
//
// group: A string representing the group (either "master", "node", or "all") to execute the command on.
//
// Returns:
//
// error: An error if the shell command fails.
//
// Example:
//
//	if err := RunReset("master"); err != nil {
//	  log.Fatalf("Failed to reset master: %v", err)
//	}
//
//	if err := RunReset("node"); err != nil {
//	  log.Fatalf("Failed to reset node: %v", err)
//	}
//
//	if err := RunReset("all"); err != nil {
//	  log.Fatalf("Failed to reset: %v", err)
//	}
func RunReset(group string) error {
	return runAnsiblePlaybook("reset.yml", group)
}

// RunAnsible executes the ansible-playbook command to provision the k8s nodes on the master or node or all,
// based on the provided group.
//
// Parameters:
//
// group: A string representing the group (either "master", "node", or "all") to provision the k8s nodes on.
//
// Returns:
//
// error: An error if the shell command fails.
//
// Example:
//
//	if err := RunAnsible("master"); err != nil {
//	  log.Fatalf("Failed to run ansible playbook on master: %v", err)
//	}
//
//	if err := RunAnsible("node"); err != nil {
//	  log.Fatalf("Failed to run ansible playbook on node: %v", err)
//	}
//
//	if err := RunAnsible("all"); err != nil {
//	  log.Fatalf("Failed to run ansible playbook: %v", err)
//	}
func RunAnsible(group string) error {
	return runAnsiblePlaybook("site.yml", group)
}

// runAnsiblePlaybook runs a specific ansible playbook on a given group of nodes.
//
// Parameters:
//
// playbook: A string representing the playbook (either "reset.yml" or "site.yml") to execute.
//
// group: A string representing the group (either "master", "node", or "all") to execute the command on.
//
// Returns:
//
// error: An error if the shell command fails.
func runAnsiblePlaybook(playbook, group string) error {
	if group != "master" && group != "node" && group != "all" {
		return fmt.Errorf("invalid group: %s. group must be 'master', 'node', or 'all'", group)
	}
	args := []string{
		filepath.Join("k3s-ansible", playbook),
		"-i",
		filepath.Join("k3s-ansible", "inventory", "cowdogmoo", "hosts.ini"),
		"--limit", group,
	}
	return runAnsibleCommand("ansible-playbook", args...)
}

// runAnsibleCommand is a helper function that runs the given ansible command with the provided arguments.
func runAnsibleCommand(cmd string, args ...string) error {
	if err := sh.RunV(cmd, args...); err != nil {
		fmt.Println(color.RedString("failed to run ansible command: %v", err))
		return err
	}
	return nil
}
