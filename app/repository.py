from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import Switch, ToggleEvent
from shared.models import SwitchState

def _as_utc_if_naive(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value

class SwitchRepository:

    def __init__(self, db: Session) -> None:
        self.db = db

    def create_switch(self, switch_id: str, name: str) -> Switch:
        switch = Switch(id=switch_id, name=name, state=SwitchState.OFF.value)
        self.db.add(switch)
        self.db.commit()
        self.db.refresh(switch)
        return switch

    def get_switch(self, switch_id: str) -> Switch | None:
        return self.db.get(Switch, switch_id)

    def list_switches(self) -> list[Switch]:
        return list(self.db.execute(select(Switch).order_by(Switch.created_at)).scalars().all())

    def switch_exists(self, switch_id: str) -> bool:
        return self.db.get(Switch, switch_id) is not None

    def update_state(self, switch_id: str, new_state: SwitchState) -> Switch:
        switch = self.db.get(Switch, switch_id)
        if switch is None:
            raise ValueError(f'Switch {switch_id} not found')
        now = datetime.now(timezone.utc)
        if new_state == SwitchState.ON and switch.state == SwitchState.OFF.value:
            switch.last_turned_on_at = now
        elif new_state == SwitchState.OFF and switch.state == SwitchState.ON.value:
            if switch.last_turned_on_at is not None:
                last_on = switch.last_turned_on_at
                if last_on.tzinfo is None:
                    last_on = last_on.replace(tzinfo=timezone.utc)
                delta = (now - last_on).total_seconds()
                switch.total_on_seconds += delta
            switch.last_turned_on_at = None
        switch.state = new_state.value
        self.db.commit()
        self.db.refresh(switch)
        return switch

    def add_toggle_event(self, switch_id: str, state: SwitchState) -> ToggleEvent:
        event = ToggleEvent(switch_id=switch_id, state=state.value, changed_at=datetime.now(timezone.utc))
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def get_toggle_events(self, switch_id: str) -> list[ToggleEvent]:
        return list(self.db.execute(select(ToggleEvent).where(ToggleEvent.switch_id == switch_id).order_by(ToggleEvent.changed_at)).scalars().all())

    def get_switch_stats(self, switch_id: str) -> dict:
        switch = self.db.get(Switch, switch_id)
        if switch is None:
            raise ValueError(f'Switch {switch_id} not found')
        events = self.get_toggle_events(switch_id)
        total_on_seconds = 0.0
        toggle_count = 0
        last_on_time: datetime | None = None
        for event in events:
            if event.state == SwitchState.ON.value:
                last_on_time = _as_utc_if_naive(event.changed_at)
                toggle_count += 1
            elif event.state == SwitchState.OFF.value and last_on_time is not None:
                off_time = _as_utc_if_naive(event.changed_at)
                delta = (off_time - last_on_time).total_seconds()
                total_on_seconds += delta
                last_on_time = None
        if switch.state == SwitchState.ON.value and last_on_time is not None:
            now = datetime.now(timezone.utc)
            total_on_seconds += (now - last_on_time).total_seconds()
        avg_session = total_on_seconds / toggle_count if toggle_count > 0 else 0.0
        return {'switch_id': switch_id, 'switch_name': switch.name, 'current_state': switch.state, 'total_on_seconds': round(total_on_seconds, 2), 'toggle_count': toggle_count, 'avg_session_seconds': round(avg_session, 2)}