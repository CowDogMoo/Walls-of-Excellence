# Set common variables for the repo.
# This is automatically pulled in through the root terragrunt.hcl configuration to
# feed forward to the child modules.
locals {
  project_name = "warpgate"
  project_owner = "cowdogmoo"
}
