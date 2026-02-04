"""Bedrock metadata helpers for model overrides."""

from __future__ import annotations

from dataclasses import dataclass, field

import boto3
from botocore.exceptions import BotoCoreError, ClientError


@dataclass(frozen=True)
class BedrockInferenceProfile:
    """Inference profile summary for UI selection."""

    inference_profile_id: str | None
    inference_profile_arn: str | None
    name: str | None
    status: str | None
    type: str | None


@dataclass(frozen=True)
class BedrockOverrides:
    """Bedrock override metadata."""

    models: list[str] = field(default_factory=list)
    inference_profiles: list[BedrockInferenceProfile] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def fetch_bedrock_overrides() -> BedrockOverrides:
    """Fetch Bedrock models and inference profiles using boto3.

    Returns empty lists if boto3 or Bedrock is unavailable.
    """
    warnings: list[str] = []
    client = boto3.client("bedrock")

    models: list[str] = []
    try:
        next_token: str | None = None
        while True:
            if next_token:
                response = client.list_foundation_models(
                    byInferenceType="ON_DEMAND", nextToken=next_token
                )
            else:
                response = client.list_foundation_models(byInferenceType="ON_DEMAND")
            for summary in response.get("modelSummaries", []):
                model_id = summary.get("modelId")
                if model_id:
                    models.append(str(model_id))
            next_token = response.get("nextToken")
            if not next_token:
                break
    except (BotoCoreError, ClientError, ValueError) as exc:
        warnings.append(f"Unable to list Bedrock on-demand models: {exc}")

    inference_profiles: list[BedrockInferenceProfile] = []
    try:
        paginator = client.get_paginator("list_inference_profiles")
        for page in paginator.paginate():
            inference_profiles.extend(
                [
                    BedrockInferenceProfile(
                        inference_profile_id=summary.get("inferenceProfileId"),
                        inference_profile_arn=summary.get("inferenceProfileArn"),
                        name=summary.get("inferenceProfileName"),
                        status=summary.get("status"),
                        type=summary.get("type"),
                    )
                    for summary in page.get("inferenceProfileSummaries", [])
                ]
            )
    except (BotoCoreError, ClientError, ValueError) as exc:
        warnings.append(f"Unable to list Bedrock inference profiles: {exc}")

    models = sorted({value for value in models if value})
    inference_profiles = sorted(
        inference_profiles,
        key=lambda profile: (
            profile.name or "",
            profile.inference_profile_id or "",
            profile.inference_profile_arn or "",
        ),
    )

    return BedrockOverrides(
        models=models,
        inference_profiles=inference_profiles,
        warnings=warnings,
    )
