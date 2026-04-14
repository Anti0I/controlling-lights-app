from __future__ import annotations
import logging
import uuid
from sqlalchemy.orm import Session
from app.models import Switch
from app.repository import SwitchRepository
from app.schemas import SwitchResponse, SwitchStatsResponse
from shared.models import SwitchState
from webapp.app.mqtt_client import get_mqtt_client
logger = logging.getLogger(__name__)

def _switch_to_response(switch: Switch) -> SwitchResponse:
    return SwitchResponse(id=switch.id, name=switch.name, state=SwitchState(switch.state), created_at=switch.created_at, total_on_seconds=switch.total_on_seconds)

def register_switch(name: str, db: Session) -> SwitchResponse:
    repo = SwitchRepository(db)
    mqtt_client = get_mqtt_client()
    switch_id = str(uuid.uuid4())
    request_id = str(uuid.uuid4())
    logger.info('Registering switch: name=%s switch_id=%s request_id=%s', name, switch_id, request_id)
    ack = mqtt_client.request_register_with_ack(request_id=request_id, switch_id=switch_id, name=name)
    if ack is None:
        raise TimeoutError(f"Simulator did not confirm registration of switch '{name}' (request_id={request_id}). Make sure the simulator is running.")
    if not ack.accepted:
        raise ValueError(f"Simulator rejected registration of switch '{name}': {ack.reason}")
    switch = repo.create_switch(switch_id=switch_id, name=name)
    logger.info('Switch registered successfully: id=%s name=%s', switch.id, switch.name)
    return _switch_to_response(switch)

def set_switch_state(switch_id: str, new_state: SwitchState, db: Session) -> SwitchResponse:
    repo = SwitchRepository(db)
    mqtt_client = get_mqtt_client()
    switch = repo.get_switch(switch_id)
    if switch is None:
        raise ValueError(f'Switch {switch_id} not found')
    if switch.state == new_state.value:
        logger.info('Switch %s is already %s', switch_id, new_state.value)
        return _switch_to_response(switch)
    switch = repo.update_state(switch_id, new_state)
    repo.add_toggle_event(switch_id, new_state)
    mqtt_client.publish_switch_command(switch_id, new_state)
    logger.info('Switch %s set to %s', switch_id, new_state.value)
    return _switch_to_response(switch)

def get_switch(switch_id: str, db: Session) -> SwitchResponse:
    repo = SwitchRepository(db)
    switch = repo.get_switch(switch_id)
    if switch is None:
        raise ValueError(f'Switch {switch_id} not found')
    return _switch_to_response(switch)

def list_switches(db: Session) -> list[SwitchResponse]:
    repo = SwitchRepository(db)
    switches = repo.list_switches()
    return [_switch_to_response(s) for s in switches]

def get_switch_stats(switch_id: str, db: Session) -> SwitchStatsResponse:
    repo = SwitchRepository(db)
    stats = repo.get_switch_stats(switch_id)
    return SwitchStatsResponse(**stats)