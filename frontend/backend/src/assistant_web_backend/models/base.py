"""Base model for API responses."""

from pydantic import BaseModel, ConfigDict


class ApiModel(BaseModel):
    """Base API model with camelCase aliases enabled."""

    model_config = ConfigDict(populate_by_name=True)
