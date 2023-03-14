# Set common variables for the environment. This is automatically pulled in in the root terragrunt.hcl configuration to
# feed forward to the child modules.
locals {
  aws_account_name   = "personal"
  env                = "prod"
  name               = "walls-of-excellence"
}
