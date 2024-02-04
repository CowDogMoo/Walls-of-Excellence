package main

import (
	"fmt"

	"github.com/bitfield/script"
	"github.com/fatih/color"
)

var (
	k8sNodes = []string{
		"k8s1",
		"k8s2",
		"k8s3",
		"k8s4",
		"k8s5",
		"k8s6",
	}
)

// RunCmdAll runs a command on all k8s nodes
// Examples:
// `mage runCmdAll 'echo "hello"'`
// `mage runCmdAll 'ip addr |grep 192'`
// `mage runCmdAll 'sudo reboot'`
func RunCmdAll(cmd string) error {
	for _, k := range k8sNodes {
		if cmd != "" {
			cmdK8s := fmt.Sprintf("ssh %s %s", k, cmd)
			fmt.Print(color.YellowString("Now running %s on %s\n", cmdK8s, k))

			if _, err := script.Exec(
				cmdK8s).Stdout(); err != nil {
				return fmt.Errorf(color.RedString(
					"error on %s: %v", k, err))
			}

		} else {
			return fmt.Errorf(color.RedString(
				"no cmd input"))
		}
	}

	return nil
}

// Reboot reboots an input node.
// If all is input, then all k8s nodes will be rebooted.
// Example:
// `mage reboot all`
func Reboot(node string) error {
	if node == "all" {
		RunCmdAll("sudo reboot")
		return nil
	}

	for _, k := range k8sNodes {
		if node == k {
			if _, err := script.Exec(
				fmt.Sprintf("ssh %s sudo reboot", k)).Stdout(); err != nil {
				return err
			}
		}
	}

	return fmt.Errorf(color.RedString(
		"%s is not a valid node", node))
}
