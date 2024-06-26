package main

import (
	"fmt"
	"path/filepath"

	"github.com/fatih/color"
	"github.com/l50/goutils/v2/sys"
)

var debug = false
var tfDir = filepath.Join("infrastructure", "prod", "repos")

// Apply runs terragrunt init, plan, and apply
func Apply() error {
	var err error

	fmt.Println(color.GreenString(
		"Now running apply on %s, please wait.\n", tfDir))

	if debug {
		_, err = sys.RunCommand(
			"terragrunt", "run-all", "apply",
			"--terragrunt-non-interactive",
			"-auto-approve",
			"-lock=false", "--terragrunt-working-dir",
			tfDir,
			"--terragrunt-log-level", "debug",
			"--terragrunt-debug")
	} else {
		_, err = sys.RunCommand(
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
		_, err = sys.RunCommand(
			"terragrunt", "run-all", "destroy",
			"--terragrunt-non-interactive", "-auto-approve",
			"-lock=false", "--terragrunt-working-dir",
			tfDir,
			"--terragrunt-log-level", "debug",
			"--terragrunt-debug")
	} else {
		_, err = sys.RunCommand(
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
