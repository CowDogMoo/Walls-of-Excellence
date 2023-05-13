//go:build mage

package main

import (
	"fmt"
	"path/filepath"

	"github.com/fatih/color"
	"github.com/magefile/mage/sh"
)

var debug = false
var tfDir = filepath.Join("infrastructure", "prod")

// Apply runs terragrunt init, plan, and apply
func Apply() error {
	var err error

	fmt.Println(color.GreenString(
		"Now running apply on %s, please wait.\n", tfDir))

	if debug {
		err = sh.RunV(
			"terragrunt", "run-all", "apply",
			"--terragrunt-non-interactive",
			"-auto-approve",
			"-lock=false", "--terragrunt-working-dir",
			tfDir,
			"--terragrunt-log-level", "debug",
			"--terragrunt-debug")
	} else {
		err = sh.RunV(
			"terragrunt", "run-all", "apply",
			"--terragrunt-non-interactive",
			"-auto-approve",
			"-lock=false", "--terragrunt-working-dir",
			tfDir)
	}
	if err != nil {
		return fmt.Errorf(color.RedString(
			"failed to apply TF modules: %v", err))
	}

	return nil
}

func Destroy() error {
	var err error

	fmt.Println(color.RedString(
		"Now destroying %s, please wait.\n", tfDir))
	if debug {
		err = sh.RunV(
			"terragrunt", "run-all", "destroy",
			"--terragrunt-non-interactive", "-auto-approve",
			"-lock=false", "--terragrunt-working-dir",
			tfDir,
			"--terragrunt-log-level", "debug",
			"--terragrunt-debug")
	} else {
		err = sh.RunV(
			"terragrunt", "run-all", "destroy",
			"--terragrunt-non-interactive", "-auto-approve",
			"-lock=false", "--terragrunt-working-dir",
			tfDir)
	}
	if err != nil {
		return fmt.Errorf(color.RedString(
			"failed to destroy TF modules: %v", err))
	}

	return nil
}
