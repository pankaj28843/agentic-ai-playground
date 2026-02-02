#!/usr/bin/env python3
"""Phoenix setup and configuration script.

This script configures Phoenix for the agentic-ai-playground project:
1. Finds or creates the project by name
2. Sets up annotation configurations for quality tracking
3. Optionally configures online evaluations with Bedrock

Usage:
    uv run python scripts/setup_phoenix.py
    uv run python scripts/setup_phoenix.py --setup-evals  # Include online evals
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from dataclasses import dataclass
from typing import Any

import httpx
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass
class PhoenixConfig:
    """Phoenix connection configuration."""

    base_url: str
    project_name: str

    @classmethod
    def from_env(cls) -> PhoenixConfig:
        """Load configuration from environment variables."""
        load_dotenv()
        base_url = os.getenv("PHOENIX_COLLECTOR_ENDPOINT")
        if not base_url:
            msg = "PHOENIX_COLLECTOR_ENDPOINT is required to configure Phoenix."
            raise ValueError(msg)
        return cls(
            base_url=base_url.rstrip("/"),
            project_name=os.getenv("PHOENIX_PROJECT_NAME", "agentic-ai-playground"),
        )


class PhoenixClient:
    """Simple HTTP client for Phoenix REST API."""

    def __init__(self, config: PhoenixConfig) -> None:
        self.config = config
        self.client = httpx.Client(base_url=config.base_url, timeout=30.0)

    def close(self) -> None:
        """Close the HTTP client."""
        self.client.close()

    def __enter__(self) -> PhoenixClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    # === Project Operations ===

    def list_projects(self) -> list[dict[str, Any]]:
        """List all projects."""
        resp = self.client.get("/v1/projects")
        resp.raise_for_status()
        return resp.json().get("data", [])

    def get_project(self, name: str) -> dict[str, Any] | None:
        """Get project by name."""
        try:
            resp = self.client.get(f"/v1/projects/{name}")
            resp.raise_for_status()
            return resp.json().get("data")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise

    def create_project(self, name: str, description: str = "") -> dict[str, Any]:
        """Create a new project."""
        resp = self.client.post(
            "/v1/projects",
            json={"name": name, "description": description},
        )
        resp.raise_for_status()
        return resp.json().get("data", {})

    def ensure_project(self) -> dict[str, Any]:
        """Ensure the project exists, creating if necessary."""
        project = self.get_project(self.config.project_name)
        if project:
            logger.info("Project '%s' exists (id=%s)", project["name"], project["id"])
            return project

        logger.info("Creating project '%s'", self.config.project_name)
        project = self.create_project(
            self.config.project_name,
            description="Agentic AI Playground - LLM agent observability",
        )
        logger.info("Created project '%s' (id=%s)", project["name"], project["id"])
        return project

    # === Annotation Config Operations ===

    def list_annotation_configs(self) -> list[dict[str, Any]]:
        """List all annotation configurations."""
        resp = self.client.get("/v1/annotation_configs")
        resp.raise_for_status()
        return resp.json().get("data", [])

    def get_annotation_config(self, name: str) -> dict[str, Any] | None:
        """Get annotation config by name."""
        try:
            resp = self.client.get(f"/v1/annotation_configs/{name}")
            resp.raise_for_status()
            return resp.json().get("data")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise

    def create_annotation_config(
        self,
        name: str,
        annotation_type: str,
        description: str = "",
        optimization_direction: str = "NONE",
        lower_bound: float | None = None,
        upper_bound: float | None = None,
        values: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Create an annotation configuration.

        Args:
            name: Unique name for the annotation
            annotation_type: One of "CATEGORICAL", "CONTINUOUS", "FREEFORM"
            description: Human-readable description
            optimization_direction: One of "NONE", "MAXIMIZE", "MINIMIZE"
            lower_bound: For CONTINUOUS type, minimum value
            upper_bound: For CONTINUOUS type, maximum value
            values: For CATEGORICAL type, list of {"label": str, "score": float}
        """
        payload: dict[str, Any] = {
            "name": name,
            "type": annotation_type,
            "description": description,
        }

        if annotation_type == "CONTINUOUS":
            payload["optimization_direction"] = optimization_direction
            if lower_bound is not None:
                payload["lower_bound"] = lower_bound
            if upper_bound is not None:
                payload["upper_bound"] = upper_bound
        elif annotation_type == "CATEGORICAL":
            payload["optimization_direction"] = optimization_direction
            if values:
                payload["values"] = values

        resp = self.client.post("/v1/annotation_configs", json=payload)
        resp.raise_for_status()
        return resp.json().get("data", {})

    def ensure_annotation_config(
        self,
        name: str,
        annotation_type: str,
        description: str = "",
        optimization_direction: str = "NONE",
        lower_bound: float | None = None,
        upper_bound: float | None = None,
        values: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Ensure annotation config exists, creating if necessary."""
        existing = self.get_annotation_config(name)
        if existing:
            logger.info("Annotation config '%s' exists", name)
            return existing

        logger.info("Creating annotation config '%s' (%s)", name, annotation_type)
        return self.create_annotation_config(
            name=name,
            annotation_type=annotation_type,
            description=description,
            optimization_direction=optimization_direction,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            values=values,
        )


def setup_annotation_configs(client: PhoenixClient) -> None:
    """Set up standard annotation configurations for agent evaluation."""
    logger.info("Setting up annotation configurations...")

    # Quality score (0-5 scale)
    client.ensure_annotation_config(
        name="quality",
        annotation_type="CONTINUOUS",
        description="Overall quality of the agent response (0-5 scale)",
        optimization_direction="MAXIMIZE",
        lower_bound=0.0,
        upper_bound=5.0,
    )

    # Helpfulness score (0-5 scale)
    client.ensure_annotation_config(
        name="helpfulness",
        annotation_type="CONTINUOUS",
        description="How helpful was the response to the user (0-5 scale)",
        optimization_direction="MAXIMIZE",
        lower_bound=0.0,
        upper_bound=5.0,
    )

    # Tool accuracy (categorical)
    client.ensure_annotation_config(
        name="tool_accuracy",
        annotation_type="CATEGORICAL",
        description="Did the agent use tools correctly",
        optimization_direction="MAXIMIZE",
        values=[
            {"label": "correct", "score": 1.0},
            {"label": "partially_correct", "score": 0.5},
            {"label": "incorrect", "score": 0.0},
        ],
    )

    # Response relevance (categorical)
    client.ensure_annotation_config(
        name="relevance",
        annotation_type="CATEGORICAL",
        description="How relevant was the response to the query",
        optimization_direction="MAXIMIZE",
        values=[
            {"label": "highly_relevant", "score": 1.0},
            {"label": "somewhat_relevant", "score": 0.5},
            {"label": "off_topic", "score": 0.0},
        ],
    )

    # User feedback (thumbs up/down)
    client.ensure_annotation_config(
        name="user_feedback",
        annotation_type="CATEGORICAL",
        description="User's explicit feedback on the response",
        optimization_direction="MAXIMIZE",
        values=[
            {"label": "positive", "score": 1.0},
            {"label": "negative", "score": 0.0},
        ],
    )

    logger.info("Annotation configurations ready")


def setup_online_evals(client: PhoenixClient) -> None:
    """Set up online evaluations with Bedrock.

    Note: Phoenix online evals require specific configuration that depends
    on the Phoenix version and deployment. This is a placeholder for future
    implementation when Phoenix's online eval API is finalized.
    """
    logger.info("Online evaluations setup...")

    # Check if AWS credentials are available
    aws_region = os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION"))
    aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")

    if not aws_region or not aws_access_key:
        logger.warning(
            "AWS credentials not found in environment. "
            "Online evals with Bedrock require AWS_REGION and AWS_ACCESS_KEY_ID."
        )
        return

    logger.info("AWS credentials found (region=%s)", aws_region)

    # Phoenix online evals are typically configured through the UI or
    # require specific API endpoints that vary by version.
    # For now, we log guidance for manual setup.
    logger.info(
        "To configure online evals with Bedrock:\n"
        "1. Open Phoenix UI: %s/settings\n"
        "2. Go to 'AI Providers' section\n"
        "3. Add AWS Bedrock provider with your credentials\n"
        "4. Configure evaluation templates in the Evaluations section",
        client.config.base_url,
    )


def print_project_info(client: PhoenixClient, project: dict[str, Any]) -> None:
    """Print useful project information and links."""
    base_url = client.config.base_url
    project_id = project.get("id", "")

    print("\n" + "=" * 60)
    print("Phoenix Project Configuration Complete")
    print("=" * 60)
    print(f"\nProject: {project.get('name')}")
    print(f"Project ID: {project_id}")
    print("\nUseful Links:")
    print(f"  Dashboard:  {base_url}/projects/{project_id}")
    print(f"  Traces:     {base_url}/projects/{project_id}/traces")
    print(f"  Spans:      {base_url}/projects/{project_id}/spans")
    print(f"  Sessions:   {base_url}/projects/{project_id}/sessions")
    print(f"  Metrics:    {base_url}/projects/{project_id}/metrics")
    print("\nREST API:")
    print(f"  Base URL:   {base_url}/v1")
    print(f"  Projects:   {base_url}/v1/projects")
    print(f"  Spans:      {base_url}/v1/projects/{project.get('name')}/spans")
    print("\nEnvironment Variables (add to .env):")
    print("  PHOENIX_ENABLED=true")
    print(f"  PHOENIX_COLLECTOR_ENDPOINT={base_url}")
    print(f"  PHOENIX_PROJECT_NAME={project.get('name')}")
    print("=" * 60 + "\n")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Configure Phoenix for agentic-ai-playground")
    parser.add_argument(
        "--setup-evals",
        action="store_true",
        help="Set up online evaluations with Bedrock",
    )
    parser.add_argument(
        "--base-url",
        help="Phoenix base URL (overrides PHOENIX_COLLECTOR_ENDPOINT)",
    )
    parser.add_argument(
        "--project-name",
        help="Project name (overrides PHOENIX_PROJECT_NAME)",
    )
    args = parser.parse_args()

    # Load configuration
    config = PhoenixConfig.from_env()
    if args.base_url:
        config = PhoenixConfig(base_url=args.base_url, project_name=config.project_name)
    if args.project_name:
        config = PhoenixConfig(base_url=config.base_url, project_name=args.project_name)

    logger.info("Connecting to Phoenix at %s", config.base_url)

    try:
        with PhoenixClient(config) as client:
            # Ensure project exists
            project = client.ensure_project()

            # Set up annotation configurations
            setup_annotation_configs(client)

            # Optionally set up online evals
            if args.setup_evals:
                setup_online_evals(client)

            # Print summary
            print_project_info(client, project)

    except httpx.ConnectError:
        logger.warning(
            "Could not connect to Phoenix at %s. Make sure Phoenix is running and accessible.",
            config.base_url,
        )
        return 1
    except httpx.HTTPStatusError as e:
        logger.warning("Phoenix API error: %s", e)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
