locals {
  env_vars = read_terragrunt_config(find_in_parent_folders("env.hcl"))
  env = local.env_vars.locals.env
  aws_region = local.env_vars.locals.aws_region
  aws_account_id = local.env_vars.locals.aws_account_id

  project_vars = read_terragrunt_config(find_in_parent_folders("project.hcl"))
  project_name = local.project_vars.locals.project_name
  project_owner = local.project_vars.locals.project_owner
}

terraform {
  source = "github.com/philips-labs/terraform-aws-github-oidc//?ref=main"
}

dependency "provider" {
  config_path = "../../provider"
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
  repo = "${local.project_owner}/${local.project_name}"
  role_name = "${local.env}-${local.project_owner}-${local.project_name}-oidc"
  default_conditions = ["allow_main"]
  role_policy_arns = ["arn:aws:iam::aws:policy/AdministratorAccess"]
  conditions = [{
    test = "StringLike"
    variable = "token.actions.githubusercontent.com:sub"
    values = [
      "repo:${local.project_owner}/${local.project_name}:pull_request",
      "repo:${local.project_owner}/${local.project_name}:refs/heads/main",
    ]
  }]
}
