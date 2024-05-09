locals {
  # Automatically load environment-level variables
  env_vars = read_terragrunt_config(find_in_parent_folders("env.hcl"))
  # Automatically load repo-level variables
  repo_vars = read_terragrunt_config(find_in_parent_folders("repo.hcl"))

  # Extract the variables we need for easy access
  aws_account_id   = "898493401173"
  aws_region       = "us-west-1"
  owner           = local.repo_vars.locals.owner

  # Local values
  repo_name            = "warpgate"
  name                 = local.env_vars.locals.name
}

terraform {
  source = "github.com/philips-labs/terraform-aws-github-oidc//?ref=main"
}

dependency "provider" {
  config_path = "../provider"
}

include {
  path = find_in_parent_folders()
}

##################################################################
# View all available inputs for this module:
# github.com/philips-labs/terraform-aws-github-oidc
##################################################################
inputs = {
  openid_connect_provider_arn = dependency.provider.outputs.openid_connect_provider.arn
  repo                        = "${local.owner}/${local.repo_name}"
  role_name                   = "${local.name}-${local.owner}-oidc"
  # override default conditions
  default_conditions          = ["allow_main"]
  role_policy_arns            = ["arn:aws:iam::aws:policy/AdministratorAccess"]

  # add extra conditions, will be merged with the default_conditions
  conditions                  = [{
    test = "StringLike"
    variable = "token.actions.githubusercontent.com:sub"
    values = ["repo:${local.owner}/${local.repo_name}:pull_request"]
  }]
}
