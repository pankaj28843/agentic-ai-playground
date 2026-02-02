# AWS IAM Setup for Bedrock & AgentCore

This directory contains IAM policy and setup scripts for creating a dedicated IAM user with minimal permissions for AWS Bedrock and AgentCore development.

## Why Use a Dedicated IAM User?

Using your AWS root account credentials for development is:
- **Insecure**: Root credentials have unrestricted access
- **Risky**: Accidental exposure can compromise your entire AWS account
- **Against AWS best practices**: AWS recommends using IAM users with least-privilege permissions

## Quick Start

```bash
# 1. Ensure AWS CLI is authenticated (choose one method)
# Method A: AWS Login (browser-based, recommended)
aws login

# Method B: AWS SSO
aws sso login --profile default

# Method C: Traditional credentials
aws configure

# 2. Verify authentication works
aws sts get-caller-identity

# 3. Run the setup script (from project root)
uv run python scripts/setup_bedrock_iam.py create

# 4. Source the updated .env file
source .env

# 5. Verify the new credentials work
aws sts get-caller-identity
# Should show: agentic-ai-playground-dev user
```

## Script Commands

| Command | Description |
|---------|-------------|
| `create` | Create IAM user, policy, and generate access keys (default) |
| `rotate` | Rotate access keys (delete old, create new) |
| `update` | Update the IAM policy to latest version from JSON file |
| `delete` | Delete IAM user and all associated resources |
| `status` | Show current IAM user and policy status |
| `env` | Output credentials in .env format |

### Examples

```bash
# Create user and generate keys
uv run python scripts/setup_bedrock_iam.py create

# Force regenerate keys for existing user
uv run python scripts/setup_bedrock_iam.py create --force

# Rotate keys (delete old, create new)
uv run python scripts/setup_bedrock_iam.py rotate

# Update policy after editing the JSON file
uv run python scripts/setup_bedrock_iam.py update

# Check status
uv run python scripts/setup_bedrock_iam.py status

# Delete user (interactive confirmation)
uv run python scripts/setup_bedrock_iam.py delete
```

## Policy Overview

The policy file `bedrock-agentcore-policy.json` grants permissions for:

### Bedrock Core
- **Model Invocation**: `bedrock:InvokeModel`, `bedrock:InvokeModelWithResponseStream`
- **Model Discovery**: List and describe foundation models, inference profiles
- **Guardrails**: Create, manage, and apply guardrails
- **Knowledge Bases**: Create, manage, and query knowledge bases

### AgentCore Services
- **Runtime**: Create and manage agent runtimes, invoke agents
- **Gateway**: Create and manage tool gateways, targets
- **Identity**: Workload identity management, credential providers
- **Memory**: Create and manage agent memory stores
- **Tools**: Browser sessions, code interpreter sessions
- **Evaluations**: Create and run agent evaluations
- **Policy**: Policy engines for agent authorization

### Supporting Services
- **IAM**: PassRole for Bedrock/AgentCore services, create service-linked roles
- **ECR**: Push/pull container images for agent deployments
- **S3**: Access buckets for AgentCore data sources
- **CloudWatch Logs**: Create and write logs
- **Secrets Manager**: Store OAuth credentials for AgentCore

## Customizing the Policy

Edit `bedrock-agentcore-policy.json` to customize permissions:

### Restrict to Specific Models
```json
{
  "Sid": "BedrockModelInvocation",
  "Effect": "Allow",
  "Action": ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
  "Resource": [
    "arn:aws:bedrock:eu-central-1::foundation-model/eu.amazon.nova-micro-v1:0",
    "arn:aws:bedrock:eu-central-1::foundation-model/anthropic.claude-3-haiku*"
  ]
}
```

### Restrict to Specific Region
```json
{
  "Condition": {
    "StringEquals": {
      "aws:RequestedRegion": "eu-central-1"
    }
  }
}
```

After editing, update the policy:
```bash
uv run python scripts/setup_bedrock_iam.py update
```

## Security Notes

1. **Credentials are gitignored**: `.env` and `.aws-credentials.json` are in `.gitignore`
2. **File permissions**: Credential files are set to `chmod 600` (owner read/write only)
3. **Key rotation**: Use `rotate` command periodically to rotate access keys
4. **Least privilege**: The policy can be further restricted for production use

## Troubleshooting

### "Access Denied" errors
- Ensure you've sourced the `.env` file: `source .env`
- Check the user has the policy attached: `uv run python scripts/setup_bedrock_iam.py status`
- Verify model access is enabled in Bedrock console

### "Model not found" errors
- Request model access in the Bedrock console
- Use the correct inference profile prefix (e.g., `eu.` or `us.`)
- Check region matches where model is available

### Script fails with "AWS session has expired"
- Re-authenticate with `aws login` or `aws sso login`
- If using AWS SSO, your session may have a limited duration

### Script fails with "AWS CLI not configured"
- Run `aws configure` with your admin credentials first
- Or set `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` environment variables
- Or use `aws login` for browser-based authentication

## References

- [AWS Bedrock AgentCore IAM Permissions](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-permissions.html)
- [BedrockAgentCoreFullAccess Managed Policy](https://docs.aws.amazon.com/aws-managed-policy/latest/reference/BedrockAgentCoreFullAccess.html)
- [Strands SDK - Amazon Bedrock Setup](https://strandsagents.com/latest/documentation/docs/user-guide/concepts/model-providers/amazon-bedrock/)
