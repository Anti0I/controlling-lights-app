from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, Field
from shared.models import SwitchState

class SwitchCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255, examples=['Salon - lampa'])

class SwitchResponse(BaseModel):
    id: str
    name: str
    state: SwitchState
    created_at: datetime
    total_on_seconds: float

class SwitchListResponse(BaseModel):
    switches: list[SwitchResponse]
    count: int

class SwitchStatsResponse(BaseModel):
    switch_id: str
    switch_name: str
    current_state: str
    total_on_seconds: float
    toggle_count: int
    avg_session_seconds: float

class MessageResponse(BaseModel):
    message: str
    switch_id: str | None = None