#!/usr/bin/env python3
"""Create/manage IAM user for Bedrock & AgentCore access.

This script creates a dedicated IAM user with minimal permissions for AWS Bedrock
and AgentCore development. It avoids using root account credentials for daily work.

USAGE:
    python scripts/setup_bedrock_iam.py [COMMAND]
    # Or if executable:
    ./scripts/setup_bedrock_iam.py [COMMAND]

COMMANDS:
    create      Create IAM user, attach policy, generate access keys (default)
    rotate      Rotate access keys (delete old, create new)
    delete      Delete IAM user and all associated resources
    status      Show current IAM user and policy status
    update      Update the IAM policy to latest version
    env         Output credentials in .env format (for manual copy)

PREREQUISITES:
    - Python 3.9+
    - boto3 installed (pip install boto3)
    - AWS CLI configured with admin/root credentials

SECURITY:
    - Access keys are written to .env file (gitignored)
    - Old keys are deleted on rotation
    - Script refuses to overwrite existing keys without --force
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError, ProfileNotFound
except ImportError:
    print("ERROR: boto3 is required. Install with: pip install boto3")
    sys.exit(1)

# Note: LoginRefreshRequired exception is detected via string matching in exception handlers
# rather than importing directly, for compatibility with older boto3 versions


# =============================================================================
# Configuration
# =============================================================================
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent
POLICY_FILE = SCRIPT_DIR / "iam" / "bedrock-agentcore-policy.json"
ENV_FILE = PROJECT_ROOT / ".env"
CREDENTIALS_FILE = PROJECT_ROOT / ".aws-credentials.json"

IAM_USER_NAME = os.environ.get("IAM_USER_NAME", "agentic-ai-playground-dev")
IAM_POLICY_NAME = os.environ.get("IAM_POLICY_NAME", "BedrockAgentCorePlaygroundPolicy")


# =============================================================================
# Color Output
# =============================================================================
class Colors:
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    NC = "\033[0m"  # No Color


def log_info(msg: str) -> None:
    print(f"{Colors.BLUE}[INFO]{Colors.NC} {msg}")


def log_success(msg: str) -> None:
    print(f"{Colors.GREEN}[OK]{Colors.NC} {msg}")


def log_warn(msg: str) -> None:
    print(f"{Colors.YELLOW}[WARN]{Colors.NC} {msg}")


def log_error(msg: str) -> None:
    print(f"{Colors.RED}[ERROR]{Colors.NC} {msg}", file=sys.stderr)


# =============================================================================
# AWS Helpers
# =============================================================================
def get_iam_client() -> Any:
    """Get IAM client with proper credential resolution."""
    try:
        session = boto3.Session()
        return session.client("iam")
    except (NoCredentialsError, ProfileNotFound) as e:
        log_error(f"AWS credentials not configured: {e}")
        log_error("Run 'aws configure' or set AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY")
        sys.exit(1)
    except Exception as e:
        if "LoginRefreshRequired" in str(type(e).__name__) or "expired" in str(e).lower():
            log_error("AWS session has expired. Please re-authenticate:")
            log_error("  Run: aws login")
            log_error("  Or: aws sso login --profile <profile-name>")
            sys.exit(1)
        raise


def get_sts_client() -> Any:
    """Get STS client for identity checks."""
    try:
        session = boto3.Session()
        return session.client("sts")
    except (NoCredentialsError, ProfileNotFound) as e:
        log_error(f"AWS credentials not configured: {e}")
        sys.exit(1)
    except Exception as e:
        if "LoginRefreshRequired" in str(type(e).__name__) or "expired" in str(e).lower():
            log_error("AWS session has expired. Please re-authenticate:")
            log_error("  Run: aws login")
            log_error("  Or: aws sso login --profile <profile-name>")
            sys.exit(1)
        raise


def get_account_id() -> str:
    """Get the AWS account ID."""
    sts = get_sts_client()
    try:
        identity = sts.get_caller_identity()
        return identity["Account"]
    except ClientError as e:
        log_error(f"Failed to get account ID: {e}")
        sys.exit(1)
    except Exception as e:
        if "LoginRefreshRequired" in str(type(e).__name__) or "expired" in str(e).lower():
            log_error("AWS session has expired. Please re-authenticate:")
            log_error("  Run: aws login")
            log_error("  Or: aws sso login --profile <profile-name>")
            sys.exit(1)
        raise


def get_policy_arn() -> str:
    """Get the full ARN for the IAM policy."""
    account_id = get_account_id()
    return f"arn:aws:iam::{account_id}:policy/{IAM_POLICY_NAME}"


def user_exists(iam: Any) -> bool:
    """Check if the IAM user exists."""
    try:
        iam.get_user(UserName=IAM_USER_NAME)
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchEntity":
            return False
        raise


def policy_exists(iam: Any) -> bool:
    """Check if the IAM policy exists."""
    try:
        iam.get_policy(PolicyArn=get_policy_arn())
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchEntity":
            return False
        raise


def load_policy_document() -> dict:
    """Load the policy JSON from file."""
    if not POLICY_FILE.exists():
        log_error(f"Policy file not found: {POLICY_FILE}")
        sys.exit(1)
    with POLICY_FILE.open() as f:
        return json.load(f)


# =============================================================================
# Commands
# =============================================================================
def cmd_status() -> None:
    """Show current IAM user and policy status."""
    log_info("Checking IAM status...")
    print()

    iam = get_iam_client()
    account_id = get_account_id()

    print(f"AWS Account: {account_id}")
    print(f"IAM User:    {IAM_USER_NAME}")
    print(f"Policy:      {IAM_POLICY_NAME}")
    print()

    # Check user
    if user_exists(iam):
        log_success(f"User '{IAM_USER_NAME}' exists")

        # List access keys
        try:
            keys = iam.list_access_keys(UserName=IAM_USER_NAME)
            if keys["AccessKeyMetadata"]:
                print("  Access Keys:")
                for key in keys["AccessKeyMetadata"]:
                    created = key["CreateDate"].strftime("%Y-%m-%d %H:%M:%S")
                    print(f"    - {key['AccessKeyId']} ({key['Status']}, created: {created})")
            else:
                log_warn("  No access keys found")
        except ClientError as e:
            log_warn(f"  Could not list access keys: {e}")

        # List attached policies
        try:
            policies = iam.list_attached_user_policies(UserName=IAM_USER_NAME)
            if policies["AttachedPolicies"]:
                policy_names = [p["PolicyName"] for p in policies["AttachedPolicies"]]
                print(f"  Attached Policies: {', '.join(policy_names)}")
        except ClientError:
            # Best-effort: listing policies may fail if user was just created or permissions are limited
            pass
    else:
        log_warn(f"User '{IAM_USER_NAME}' does not exist")

    print()

    # Check policy
    if policy_exists(iam):
        log_success(f"Policy '{IAM_POLICY_NAME}' exists")
        try:
            policy_arn = get_policy_arn()
            versions = iam.list_policy_versions(PolicyArn=policy_arn)
            if versions["Versions"]:
                print("  Policy Versions:")
                for ver in versions["Versions"]:
                    default_marker = " (default)" if ver["IsDefaultVersion"] else ""
                    print(f"    - {ver['VersionId']}{default_marker}")
        except ClientError:
            # Best-effort: listing versions may fail if policy permissions are limited
            pass
    else:
        log_warn(f"Policy '{IAM_POLICY_NAME}' does not exist")

    print()

    # Check .env file
    if ENV_FILE.exists():
        content = ENV_FILE.read_text()
        if "AWS_ACCESS_KEY_ID" in content and content.count("AWS_ACCESS_KEY_ID") != content.count(
            "# export AWS_ACCESS_KEY_ID"
        ):
            log_success(".env file contains AWS credentials")
        else:
            log_warn(".env file exists but has no AWS credentials")
    else:
        log_warn(".env file does not exist")


def cmd_create(force: bool = False) -> None:
    """Create IAM user, attach policy, and generate access keys."""
    log_info(f"Creating IAM user '{IAM_USER_NAME}' for Bedrock/AgentCore access...")

    iam = get_iam_client()
    policy_arn = get_policy_arn()

    # Create or update policy
    if policy_exists(iam):
        log_info(f"Policy '{IAM_POLICY_NAME}' already exists, updating...")
        cmd_update()
    else:
        log_info(f"Creating policy '{IAM_POLICY_NAME}'...")
        policy_doc = load_policy_document()
        iam.create_policy(
            PolicyName=IAM_POLICY_NAME,
            PolicyDocument=json.dumps(policy_doc),
            Description="Bedrock and AgentCore access for playground development",
        )
        log_success(f"Policy created: {policy_arn}")

    # Create user if not exists
    if user_exists(iam):
        log_warn(f"User '{IAM_USER_NAME}' already exists")
        if not force:
            log_info("Use --force to regenerate access keys")
            log_info("Or use 'rotate' command to rotate keys")
            return
    else:
        log_info(f"Creating user '{IAM_USER_NAME}'...")
        iam.create_user(UserName=IAM_USER_NAME)
        log_success("User created")

    # Attach policy to user
    try:
        attached = iam.list_attached_user_policies(UserName=IAM_USER_NAME)
        attached_arns = [p["PolicyArn"] for p in attached["AttachedPolicies"]]
        if policy_arn not in attached_arns:
            log_info("Attaching policy to user...")
            iam.attach_user_policy(UserName=IAM_USER_NAME, PolicyArn=policy_arn)
            log_success("Policy attached")
        else:
            log_info("Policy already attached to user")
    except ClientError as e:
        log_error(f"Failed to attach policy: {e}")
        sys.exit(1)

    # Generate access keys
    generate_access_keys(iam, force=force)

    log_success("IAM setup complete!")
    print()
    log_info(f"Credentials have been written to: {ENV_FILE}")
    log_info(f"Run 'source {ENV_FILE}' to load them into your shell")


def generate_access_keys(iam: Any, force: bool = False) -> None:
    """Generate new access keys for the IAM user."""
    # Check existing keys
    existing_keys = iam.list_access_keys(UserName=IAM_USER_NAME)["AccessKeyMetadata"]

    if existing_keys:
        if not force:
            key_ids = [k["AccessKeyId"] for k in existing_keys]
            log_warn(f"User already has access keys: {', '.join(key_ids)}")
            log_info("Use --force to delete and regenerate, or 'rotate' to rotate keys")
            return

        # Delete existing keys
        for key in existing_keys:
            log_info(f"Deleting existing key: {key['AccessKeyId']}")
            iam.delete_access_key(UserName=IAM_USER_NAME, AccessKeyId=key["AccessKeyId"])

    # Create new access key
    log_info("Generating new access key...")
    key_response = iam.create_access_key(UserName=IAM_USER_NAME)
    access_key = key_response["AccessKey"]

    access_key_id = access_key["AccessKeyId"]
    secret_access_key = access_key["SecretAccessKey"]

    # Save to credentials file (backup)
    # Convert datetime to string for JSON serialization
    key_data = {
        "AccessKey": {
            "AccessKeyId": access_key_id,
            "SecretAccessKey": secret_access_key,
            "CreateDate": access_key["CreateDate"].isoformat(),
            "UserName": access_key["UserName"],
            "Status": access_key["Status"],
        }
    }
    # Save to credentials file with secure permissions from creation time
    # Use os.open() to create file with restricted permissions atomically
    credentials_path = str(CREDENTIALS_FILE)
    fd = os.open(credentials_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(key_data, f, indent=2)
    except Exception:
        # If fdopen fails, ensure fd is closed
        with contextlib.suppress(OSError):
            os.close(fd)
        raise
    # Ensure permissions are correct on POSIX systems even if file pre-existed
    if os.name != "nt":
        try:
            CREDENTIALS_FILE.chmod(0o600)
        except OSError as exc:
            log_warn(f"Could not set permissions on {CREDENTIALS_FILE}: {exc}")
    log_info(f"Credentials backup saved to: {CREDENTIALS_FILE}")

    # Update .env file
    update_env_file(access_key_id, secret_access_key)

    log_success(f"Access key created: {access_key_id}")


def update_env_file(access_key_id: str, secret_access_key: str) -> None:
    """Update the .env file with new credentials."""
    # Create .env if it doesn't exist
    if not ENV_FILE.exists():
        env_example = PROJECT_ROOT / ".env.example"
        if env_example.exists():
            ENV_FILE.write_text(env_example.read_text())
        else:
            ENV_FILE.touch()

    # Read current content and filter out old AWS credential lines
    content = ENV_FILE.read_text()
    lines = content.splitlines()

    # Filter out AWS credential lines (both commented and uncommented)
    filtered_lines = []
    aws_cred_keys = [
        "AWS_ACCESS_KEY_ID=",
        "AWS_SECRET_ACCESS_KEY=",
        "AWS_SESSION_TOKEN=",
        "AWS_PROFILE=",
    ]
    for line in lines:
        stripped = line.strip()
        # Skip lines that set AWS credentials (commented or not)
        # Check if line contains any AWS credential key with an equals sign
        if any(k in stripped for k in aws_cred_keys) and "=" in stripped:
            continue
        # Also skip the generated comment headers
        if "# AWS IAM User:" in line or "# Generated:" in line:
            continue
        filtered_lines.append(line)

    # Remove trailing empty lines
    while filtered_lines and not filtered_lines[-1].strip():
        filtered_lines.pop()

    # Add new credentials
    timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    filtered_lines.extend(
        [
            "",
            f"# AWS IAM User: {IAM_USER_NAME}",
            f"# Generated: {timestamp}",
            f'export AWS_ACCESS_KEY_ID="{access_key_id}"',
            f'export AWS_SECRET_ACCESS_KEY="{secret_access_key}"',
        ]
    )

    # Write back with secure permissions from creation time
    data = "\n".join(filtered_lines) + "\n"
    env_path = str(ENV_FILE)
    fd = os.open(env_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(data)
    except Exception:
        # If fdopen fails, ensure fd is closed
        with contextlib.suppress(OSError):
            os.close(fd)
        raise
    # Ensure permissions are correct on POSIX systems even if file pre-existed
    if os.name != "nt":
        try:
            ENV_FILE.chmod(0o600)
        except OSError as exc:
            log_warn(f"Could not set POSIX permissions on {ENV_FILE}: {exc}")

    log_success(f"Updated {ENV_FILE} with new credentials")


def cmd_rotate() -> None:
    """Rotate access keys (delete old, create new)."""
    log_info(f"Rotating access keys for '{IAM_USER_NAME}'...")

    iam = get_iam_client()

    if not user_exists(iam):
        log_error(f"User '{IAM_USER_NAME}' does not exist. Run 'create' first.")
        sys.exit(1)

    generate_access_keys(iam, force=True)
    log_success("Key rotation complete!")


def cmd_update() -> None:
    """Update the IAM policy to the latest version."""
    log_info(f"Updating IAM policy '{IAM_POLICY_NAME}'...")

    iam = get_iam_client()
    policy_arn = get_policy_arn()

    if not policy_exists(iam):
        log_error("Policy does not exist. Run 'create' first.")
        sys.exit(1)

    # Get current versions
    versions = iam.list_policy_versions(PolicyArn=policy_arn)["Versions"]
    version_count = len(versions)

    # AWS allows max 5 versions, delete oldest non-default if at limit
    if version_count >= 5:
        log_info("Cleaning up old policy versions (max 5 allowed)...")
        # Find oldest non-default version
        non_default = [v for v in versions if not v["IsDefaultVersion"]]
        if non_default:
            # Sort by create date and delete oldest
            oldest = sorted(non_default, key=lambda v: v["CreateDate"])[0]
            iam.delete_policy_version(PolicyArn=policy_arn, VersionId=oldest["VersionId"])
            log_info(f"Deleted old version: {oldest['VersionId']}")

    # Create new version
    log_info("Creating new policy version...")
    policy_doc = load_policy_document()
    iam.create_policy_version(
        PolicyArn=policy_arn,
        PolicyDocument=json.dumps(policy_doc),
        SetAsDefault=True,
    )

    log_success("Policy updated to latest version")


def cmd_delete() -> None:
    """Delete IAM user and all associated resources."""
    log_info(f"Deleting IAM user '{IAM_USER_NAME}' and associated resources...")

    print()
    log_warn("This will delete:")
    print(f"  - IAM User: {IAM_USER_NAME}")
    print("  - All access keys for this user")
    print("  - Policy attachment (policy itself preserved)")
    print()

    confirm = input("Are you sure? (yes/no): ")
    if confirm.lower() != "yes":
        log_info("Aborted")
        return

    iam = get_iam_client()

    if user_exists(iam):
        # Delete access keys
        keys = iam.list_access_keys(UserName=IAM_USER_NAME)["AccessKeyMetadata"]
        for key in keys:
            log_info(f"Deleting access key: {key['AccessKeyId']}")
            iam.delete_access_key(UserName=IAM_USER_NAME, AccessKeyId=key["AccessKeyId"])

        # Detach policies
        try:
            attached = iam.list_attached_user_policies(UserName=IAM_USER_NAME)
            for policy in attached["AttachedPolicies"]:
                log_info(f"Detaching policy: {policy['PolicyName']}")
                iam.detach_user_policy(UserName=IAM_USER_NAME, PolicyArn=policy["PolicyArn"])
        except ClientError as e:
            # Best-effort: log failure but continue with deletion so cleanup can proceed
            log_warn(f"Failed to list or detach user policies for '{IAM_USER_NAME}': {e}")

        # Delete user
        log_info("Deleting user...")
        iam.delete_user(UserName=IAM_USER_NAME)
        log_success("User deleted")
    else:
        log_warn(f"User '{IAM_USER_NAME}' does not exist")

    # Ask about deleting policy
    if policy_exists(iam):
        print()
        confirm_policy = input(f"Also delete the policy '{IAM_POLICY_NAME}'? (yes/no): ")
        if confirm_policy.lower() == "yes":
            policy_arn = get_policy_arn()

            # Delete all non-default versions first
            versions = iam.list_policy_versions(PolicyArn=policy_arn)["Versions"]
            for ver in versions:
                if not ver["IsDefaultVersion"]:
                    log_info(f"Deleting policy version: {ver['VersionId']}")
                    iam.delete_policy_version(PolicyArn=policy_arn, VersionId=ver["VersionId"])

            log_info("Deleting policy...")
            iam.delete_policy(PolicyArn=policy_arn)
            log_success("Policy deleted")

    # Clean up local credentials
    if CREDENTIALS_FILE.exists():
        CREDENTIALS_FILE.unlink()
        log_info("Removed credentials file")

    log_success("Cleanup complete")


def cmd_env() -> None:
    """Output credentials in .env format."""
    if not CREDENTIALS_FILE.exists():
        log_error("No credentials file found. Run 'create' first.")
        sys.exit(1)

    with CREDENTIALS_FILE.open() as f:
        data = json.load(f)

    access_key_id = data["AccessKey"]["AccessKeyId"]
    secret_access_key = data["AccessKey"]["SecretAccessKey"]

    print(f"# AWS Credentials for {IAM_USER_NAME}")
    print(f'export AWS_ACCESS_KEY_ID="{access_key_id}"')
    print(f'export AWS_SECRET_ACCESS_KEY="{secret_access_key}"')


# =============================================================================
# Main
# =============================================================================
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create/manage IAM user for Bedrock & AgentCore access",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  create      Create IAM user, attach policy, generate access keys (default)
  rotate      Rotate access keys (delete old, create new)
  delete      Delete IAM user and all associated resources
  status      Show current IAM user and policy status
  update      Update the IAM policy to latest version
  env         Output credentials in .env format (for manual copy)

Examples:
  %(prog)s create           # Create user and generate keys
  %(prog)s create --force   # Force regenerate keys for existing user
  %(prog)s rotate           # Rotate keys (delete old, create new)
  %(prog)s status           # Check current status
  %(prog)s update           # Update policy after editing JSON
  %(prog)s delete           # Delete user (interactive)
""",
    )

    parser.add_argument(
        "command",
        nargs="?",
        default="create",
        choices=["create", "rotate", "delete", "status", "update", "env"],
        help="Command to execute (default: create)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force regenerate access keys for existing user",
    )

    args = parser.parse_args()

    try:
        if args.command == "create":
            cmd_create(force=args.force)
        elif args.command == "rotate":
            cmd_rotate()
        elif args.command == "delete":
            cmd_delete()
        elif args.command == "status":
            cmd_status()
        elif args.command == "update":
            cmd_update()
        elif args.command == "env":
            cmd_env()
    except ClientError as e:
        log_error(f"AWS API error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print()
        log_info("Aborted")
        sys.exit(0)


if __name__ == "__main__":
    main()
