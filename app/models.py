"""Shared Pydantic model policies for the application's architectural boundaries."""

from pydantic import BaseModel, ConfigDict


def replace_model[ModelT: BaseModel](model: ModelT, **changes: object) -> ModelT:
    """Return an updated Pydantic model without mutating the original instance."""
    return model.model_copy(update=changes)


class EntityModel(BaseModel):
    """Base for mutable domain state with validated assignments."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class CommandModel(BaseModel):
    """Base for immutable application input models."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class ApiModel(BaseModel):
    """Base for strict HTTP request and webhook models."""

    model_config = ConfigDict(extra="forbid")


class ApiResponseModel(ApiModel):
    """Base for response models built from domain object attributes."""

    model_config = ConfigDict(from_attributes=True)
