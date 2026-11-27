"""Shared Pydantic response and pagination models."""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class APIModel(BaseModel):
    """Common settings for API schemas."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class PageParams(APIModel):
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)

    @field_validator("limit", "offset", mode="before")
    @classmethod
    def reject_boolean_pagination_values(cls, value: object) -> object:
        """Prevent JSON booleans from being accepted as integer parameters."""
        if isinstance(value, bool):
            raise ValueError("pagination values must be integers")
        return value


class DateRangeParams(APIModel):
    start_date: date | None = None
    end_date: date | None = None

    @model_validator(mode="after")
    def validate_date_order(self):
        """Ensure a supplied date range is chronological."""
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("start_date must be on or before end_date")
        return self


class PaginationMeta(APIModel):
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)
    returned: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_returned_count(self):
        """Ensure a page cannot report more rows than its requested limit or total."""
        if self.returned > self.limit:
            raise ValueError("returned cannot be greater than limit")
        if self.returned > self.total:
            raise ValueError("returned cannot be greater than total")
        return self


class ErrorDetail(APIModel):
    code: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=500)
    field: str | None = Field(default=None, max_length=100)

    @field_validator("code", "message", "field", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        """Trim API error text while preserving optional null fields."""
        return value.strip() if isinstance(value, str) else value


class ErrorResponse(APIModel):
    error: ErrorDetail
