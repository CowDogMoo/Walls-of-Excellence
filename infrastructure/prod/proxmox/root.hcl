# ---------------------------------------------------------------------------------------------------------------------
# TERRAGRUNT CONFIGURATION FOR PROXMOX
# ---------------------------------------------------------------------------------------------------------------------
locals {
  # Automatically load environment-level variables
  env_vars = read_terragrunt_config(find_in_parent_folders("env.hcl"))

  # Proxmox connection details - these should be set as environment variables:
  # export PM_API_URL="https://proxmox:8006/api2/json"
  # export PM_USER="root@pam"
  # export PM_PASS="your-password"
  # Or use API token:
  # export PM_API_TOKEN_ID="user@pam!token_id"
  # export PM_API_TOKEN_SECRET="token-secret"
}

generate "provider" {
  path      = "provider.tf"
  if_exists = "overwrite_terragrunt"
  contents  = <<EOF
provider "proxmox" {
  endpoint = var.proxmox_endpoint
  api_token = var.proxmox_api_token
  insecure = true
}

variable "proxmox_endpoint" {
  description = "Proxmox API endpoint"
  type        = string
  default     = ""
}

variable "proxmox_api_token" {
  description = "Proxmox API token in format USER@REALM!TOKENID=SECRET"
  type        = string
  sensitive   = true
  default     = ""
}
EOF
}

# Configure Terragrunt to automatically store tfstate files in an S3 bucket
remote_state {
  backend = "s3"
  config = {
    encrypt        = true
    bucket         = "walls-of-excellence"
    key            = "proxmox/${path_relative_to_include()}/terraform.tfstate"
    region         = local.env_vars.locals.aws_region
    dynamodb_table = "walls-of-excellence-tfstate"
  }
  generate = {
    path      = "backend.tf"
    if_exists = "overwrite_terragrunt"
  }
}

inputs = merge(
  local.env_vars.locals,
  {
    proxmox_endpoint = get_env("PM_API_URL", "")
    proxmox_api_token = "${get_env("PM_API_TOKEN_ID", "")}=${get_env("PM_API_TOKEN_SECRET", "")}"
  }
)
