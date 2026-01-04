# Set common variables for the environment. This is automatically pulled in in the root terragrunt.hcl configuration to
# feed forward to the child modules.
locals {
  # Injected from 1Password: op item get "AWS (Amazon Web Services)" --vault automation
  aws_account_id = "op://automation/ev2iikf4tydkhgo5chx6goyjme/aws_account_id"
  aws_region     = "us-west-1"
  env            = "prod"
}
