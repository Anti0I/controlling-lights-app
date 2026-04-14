from __future__ import annotations
import uuid
from datetime import datetime
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base

class Switch(Base):
    __tablename__ = 'switches'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    state: Mapped[str] = mapped_column(String(3), nullable=False, default='off')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    total_on_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    last_turned_on_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    toggle_events: Mapped[list[ToggleEvent]] = relationship('ToggleEvent', back_populates='switch', cascade='all, delete-orphan')

class ToggleEvent(Base):
    __tablename__ = 'toggle_events'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    switch_id: Mapped[str] = mapped_column(String(36), ForeignKey('switches.id', ondelete='CASCADE'), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(3), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    switch: Mapped[Switch] = relationship('Switch', back_populates='toggle_events')