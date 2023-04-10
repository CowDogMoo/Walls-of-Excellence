//go:build mage

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

var (
	modules = []string{
		"provider",
		"awsutils",
	}
	debug = false
	tfDir = filepath.Join("infrastructure", "prod")
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

func UninstallFlux() error {
	var err error

	fmt.Println(color.GreenString(
		"Uninstalling flux, please wait.\n", tfDir))

	if err := sh.RunV("flux", "uninstall"); err != nil {
		return err
	}

	if err != nil {
		return fmt.Errorf(color.RedString(
			"failed to apply TF modules: %v", err))
	}

	return nil
}
