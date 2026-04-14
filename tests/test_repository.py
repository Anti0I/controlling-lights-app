from __future__ import annotations
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from app.database import Base
from app.repository import SwitchRepository
from shared.models import SwitchState

@pytest.fixture()
def db_session():
    engine = create_engine('sqlite:///:memory:', connect_args={'check_same_thread': False})
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)

class TestCreateSwitch:

    def test_create_switch(self, db_session: Session) -> None:
        repo = SwitchRepository(db_session)
        switch = repo.create_switch('switch-1', 'Salon')
        assert switch.id == 'switch-1'
        assert switch.name == 'Salon'
        assert switch.state == 'off'
        assert switch.total_on_seconds == 0.0

    def test_create_switch_persists_in_db(self, db_session: Session) -> None:
        repo = SwitchRepository(db_session)
        repo.create_switch('switch-2', 'Kuchnia')
        fetched = repo.get_switch('switch-2')
        assert fetched is not None
        assert fetched.name == 'Kuchnia'

class TestGetSwitch:

    def test_get_existing_switch(self, db_session: Session) -> None:
        repo = SwitchRepository(db_session)
        repo.create_switch('abc-123', 'Lampa')
        result = repo.get_switch('abc-123')
        assert result is not None
        assert result.name == 'Lampa'

    def test_get_nonexistent_switch_returns_none(self, db_session: Session) -> None:
        repo = SwitchRepository(db_session)
        result = repo.get_switch('nonexistent')
        assert result is None

class TestListSwitches:

    def test_list_empty(self, db_session: Session) -> None:
        repo = SwitchRepository(db_session)
        assert repo.list_switches() == []

    def test_list_multiple(self, db_session: Session) -> None:
        repo = SwitchRepository(db_session)
        repo.create_switch('s1', 'Salon')
        repo.create_switch('s2', 'Kuchnia')
        switches = repo.list_switches()
        assert len(switches) == 2

class TestUpdateState:

    def test_turn_on(self, db_session: Session) -> None:
        repo = SwitchRepository(db_session)
        repo.create_switch('s1', 'Test')
        switch = repo.update_state('s1', SwitchState.ON)
        assert switch.state == 'on'
        assert switch.last_turned_on_at is not None

    def test_turn_off_accumulates_time(self, db_session: Session) -> None:
        repo = SwitchRepository(db_session)
        repo.create_switch('s1', 'Test')
        repo.update_state('s1', SwitchState.ON)
        switch = repo.update_state('s1', SwitchState.OFF)
        assert switch.state == 'off'
        assert switch.last_turned_on_at is None
        assert switch.total_on_seconds >= 0.0

    def test_update_nonexistent_raises(self, db_session: Session) -> None:
        repo = SwitchRepository(db_session)
        with pytest.raises(ValueError, match='not found'):
            repo.update_state('nonexistent', SwitchState.ON)

class TestToggleEvents:

    def test_add_toggle_event(self, db_session: Session) -> None:
        repo = SwitchRepository(db_session)
        repo.create_switch('s1', 'Test')
        event = repo.add_toggle_event('s1', SwitchState.ON)
        assert event.switch_id == 's1'
        assert event.state == 'on'

    def test_get_toggle_events(self, db_session: Session) -> None:
        repo = SwitchRepository(db_session)
        repo.create_switch('s1', 'Test')
        repo.add_toggle_event('s1', SwitchState.ON)
        repo.add_toggle_event('s1', SwitchState.OFF)
        repo.add_toggle_event('s1', SwitchState.ON)
        events = repo.get_toggle_events('s1')
        assert len(events) == 3
        assert events[0].state == 'on'
        assert events[1].state == 'off'
        assert events[2].state == 'on'

class TestSwitchStats:

    def test_stats_no_events(self, db_session: Session) -> None:
        repo = SwitchRepository(db_session)
        repo.create_switch('s1', 'Test')
        stats = repo.get_switch_stats('s1')
        assert stats['toggle_count'] == 0
        assert stats['total_on_seconds'] == 0.0
        assert stats['avg_session_seconds'] == 0.0

    def test_stats_with_events(self, db_session: Session) -> None:
        repo = SwitchRepository(db_session)
        repo.create_switch('s1', 'Test')
        repo.add_toggle_event('s1', SwitchState.ON)
        repo.add_toggle_event('s1', SwitchState.OFF)
        stats = repo.get_switch_stats('s1')
        assert stats['toggle_count'] == 1
        assert stats['total_on_seconds'] >= 0.0

    def test_stats_nonexistent_raises(self, db_session: Session) -> None:
        repo = SwitchRepository(db_session)
        with pytest.raises(ValueError, match='not found'):
            repo.get_switch_stats('nonexistent')