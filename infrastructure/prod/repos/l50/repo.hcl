# Set common variables for the repo.
# This is automatically pulled in through the root terragrunt.hcl configuration to
# feed forward to the child modules.
locals {
  common_vars = read_terragrunt_config(find_in_parent_folders("env.hcl"))
  repo_vars = read_terragrunt_config(find_in_parent_folders("repo.hcl"))

  project_name = "awsutils"
  aws_region = local.repo_vars.locals.default_region
}

terraform {
  source = "github.com/philips-labs/terraform-aws-github-oidc//?ref=main"
}

include {
  path = find_in_parent_folders()
}

inputs = {
  region = local.aws_region
}
