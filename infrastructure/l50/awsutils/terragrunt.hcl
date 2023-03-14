locals {
  # Automatically load environment-level variables
  env_vars = read_terragrunt_config(find_in_parent_folders("env.hcl"))

  # Extract the variables we need for easy access
  aws_account_id  = local.env_vars.locals.aws_account_id
  aws_region      = local.env_vars.locals.aws_region
  owner           = local.env_vars.locals.owner

  # Local values
  name            = "awsutils"
  repo            = "${owner}/${name}"
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
  openid_connect_provider_arn = dependency.provider.outputs.oidc_provider.openid_connect_provider.arn
  repo                        = local.repo
  role_name                   = "${local.repo}-s3"
  # override default conditions
  default_conditions          = ["allow_main"]

  # add extra conditions, will be merged with the default_conditions
  conditions                  = [{
    test = "StringLike"
    variable = "token.actions.githubusercontent.com:sub"
    values = ["repo:${local.repo}:pull_request"]
  }]
}
