package main

import (
	"fmt"
	"path/filepath"

	"github.com/fatih/color"
	"github.com/magefile/mage/sh"
)

// runAnsibleCommand is a helper function that runs the given ansible command with the provided arguments.
func runAnsibleCommand(cmd string, args ...string) error {
	if err := sh.RunV(cmd, args...); err != nil {
		fmt.Println(color.RedString("failed to run ansible command: %v", err))
		return err
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

// RunAnsible executes the ansible-playbook command to provision the k8s nodes on the master or node or both,
// based on the provided group. If no group is specified, the command is executed on all groups.
//
// Parameters:
//
// group: An optional string representing the group (either "master" or "node") to provision the k8s nodes on.
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
//	if err := RunAnsible(); err != nil {
//	  log.Fatalf("Failed to run ansible playbook: %v", err)
//	}
func RunAnsible(group string) error {
	args := []string{
		filepath.Join("k3s-ansible", "site.yml"),
		"-i",
		filepath.Join("k3s-ansible", "inventory", "cowdogmoo", "hosts.ini"),
	}
	if len(group) > 0 {
		args = append(args, "--limit", group)
	} else {
		args = append(args, "--limit", "all")
	}
	return runAnsibleCommand("ansible-playbook", args...)
}

// RunReset executes the 'ansible-playbook' command with the 'reset.yml' playbook on the master or node or both,
// based on the provided group. If no group is specified, the command is executed on the node group.
//
// Parameters:
//
// group: An optional string representing the group (either "master" or "node") to execute the command on.
//
// Returns:
//
// error: An error if the shell command fails.
//
// Example:
//
//	if err := RunReset("master"); err != nil {
//	  log.Fatalf("failed to reset master nodes: %v", err)
//	}
//
//	if err := RunReset("node"); err != nil {
//	  log.Fatalf("failed to reset nodes: %v", err)
//	}
//
//	if err := RunReset(); err != nil {
//	  log.Fatalf("failed to reset all managed nodes: %v", err)
//	}
func RunReset(group string) error {
	args := []string{
		filepath.Join("k3s-ansible", "reset.yml"),
		"-i",
		filepath.Join("k3s-ansible", "inventory", "cowdogmoo", "hosts.ini"),
	}
	if len(group) > 0 {
		args = append(args, "--limit", group)
	} else {
		args = append(args, "--limit", "node")
	}
	return runAnsibleCommand("ansible-playbook", args...)
}
