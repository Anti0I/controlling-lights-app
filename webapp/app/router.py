from __future__ import annotations
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import SwitchCreate, SwitchListResponse, SwitchResponse, SwitchStatsResponse
from shared.models import SwitchState
from webapp.app import service
logger = logging.getLogger(__name__)
router = APIRouter(prefix='/switches', tags=['switches'])

@router.post('', response_model=SwitchResponse, status_code=201)
def create_switch(body: SwitchCreate, db: Session=Depends(get_db)) -> SwitchResponse:
    try:
        return service.register_switch(name=body.name, db=db)
    except TimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@router.get('', response_model=SwitchListResponse)
def list_switches(db: Session=Depends(get_db)) -> SwitchListResponse:
    switches = service.list_switches(db=db)
    return SwitchListResponse(switches=switches, count=len(switches))

@router.get('/{switch_id}', response_model=SwitchResponse)
def get_switch(switch_id: str, db: Session=Depends(get_db)) -> SwitchResponse:
    try:
        return service.get_switch(switch_id=switch_id, db=db)
    except ValueError:
        raise HTTPException(status_code=404, detail=f'Switch {switch_id} not found')

@router.post('/{switch_id}/on', response_model=SwitchResponse)
def turn_on(switch_id: str, db: Session=Depends(get_db)) -> SwitchResponse:
    try:
        return service.set_switch_state(switch_id=switch_id, new_state=SwitchState.ON, db=db)
    except ValueError:
        raise HTTPException(status_code=404, detail=f'Switch {switch_id} not found')

@router.post('/{switch_id}/off', response_model=SwitchResponse)
def turn_off(switch_id: str, db: Session=Depends(get_db)) -> SwitchResponse:
    try:
        return service.set_switch_state(switch_id=switch_id, new_state=SwitchState.OFF, db=db)
    except ValueError:
        raise HTTPException(status_code=404, detail=f'Switch {switch_id} not found')

@router.get('/{switch_id}/stats', response_model=SwitchStatsResponse)
def get_stats(switch_id: str, db: Session=Depends(get_db)) -> SwitchStatsResponse:
    try:
        return service.get_switch_stats(switch_id=switch_id, db=db)
    except ValueError:
        raise HTTPException(status_code=404, detail=f'Switch {switch_id} not found')