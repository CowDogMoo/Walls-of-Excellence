# Set common variables for the environment.
# This is automatically pulled in through the root terragrunt.hcl configuration to
# feed forward to the child modules.
locals {
  aws_account_id  = "898493401173"
  aws_region = "us-west-1"
  owner = "l50"
}
