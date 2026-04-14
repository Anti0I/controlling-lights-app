from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Self
from pydantic import BaseModel, ConfigDict, Field, model_validator

class HealthResponse(BaseModel):
    status: str = Field(default='ok')

class SwitchState(str, Enum):
    ON = 'on'
    OFF = 'off'

class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    request_id: str = Field(min_length=1, max_length=64)
    switch_id: str = Field(min_length=1, max_length=64, pattern='^[A-Za-z0-9_-]+$')
    name: str = Field(min_length=1, max_length=128)

class RegisterAck(BaseModel):
    model_config = ConfigDict(extra='forbid')
    request_id: str = Field(min_length=1, max_length=64)
    switch_id: str = Field(min_length=1, max_length=64, pattern='^[A-Za-z0-9_-]+$')
    accepted: bool
    reason: str | None = Field(default=None, min_length=1, max_length=256)

    @model_validator(mode='after')
    def validate_reason(self) -> Self:
        if self.accepted and self.reason is not None:
            raise ValueError('reason must be omitted when accepted is true')
        if not self.accepted and self.reason is None:
            raise ValueError('reason is required when accepted is false')
        return self

class SwitchSetCommand(BaseModel):
    model_config = ConfigDict(extra='forbid')
    switch_id: str = Field(min_length=1, max_length=64, pattern='^[A-Za-z0-9_-]+$')
    state: SwitchState
    sent_at: datetime

    @model_validator(mode='after')
    def validate_sent_at_timezone(self) -> Self:
        if self.sent_at.tzinfo is None or self.sent_at.utcoffset() is None:
            raise ValueError('sent_at must include timezone information')
        return self