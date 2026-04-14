from __future__ import annotations
import re
from dataclasses import dataclass
from enum import Enum
from typing import Final
REGISTER_REQUEST_TOPIC: Final[str] = 'lighting/switch/register/request'
REGISTER_ACK_TOPIC: Final[str] = 'lighting/switch/register/ack'
SWITCH_SET_TOPIC_TEMPLATE: Final[str] = 'lighting/switch/{switch_id}/set'
_SWITCH_ID_PATTERN: Final[re.Pattern[str]] = re.compile('^[A-Za-z0-9_-]+$')
_SWITCH_SET_TOPIC_PATTERN: Final[re.Pattern[str]] = re.compile('^lighting/switch/(?P<switch_id>[A-Za-z0-9_-]+)/set$')

class TopicKind(str, Enum):
    REGISTER_REQUEST = 'register_request'
    REGISTER_ACK = 'register_ack'
    SWITCH_SET = 'switch_set'

@dataclass(frozen=True, slots=True)
class ParsedTopic:
    kind: TopicKind
    switch_id: str | None = None

def _validate_switch_id(switch_id: str) -> str:
    if not _SWITCH_ID_PATTERN.fullmatch(switch_id):
        raise ValueError('switch_id must match ^[A-Za-z0-9_-]+$')
    return switch_id

def build_register_request_topic() -> str:
    return REGISTER_REQUEST_TOPIC

def build_register_ack_topic() -> str:
    return REGISTER_ACK_TOPIC

def build_switch_set_topic(switch_id: str) -> str:
    return SWITCH_SET_TOPIC_TEMPLATE.format(switch_id=_validate_switch_id(switch_id))

def parse_switch_set_topic(topic: str) -> str:
    match = _SWITCH_SET_TOPIC_PATTERN.fullmatch(topic)
    if match is None:
        raise ValueError('topic does not match lighting/switch/{switch_id}/set')
    return match.group('switch_id')

def parse_contract_topic(topic: str) -> ParsedTopic:
    if topic == REGISTER_REQUEST_TOPIC:
        return ParsedTopic(kind=TopicKind.REGISTER_REQUEST)
    if topic == REGISTER_ACK_TOPIC:
        return ParsedTopic(kind=TopicKind.REGISTER_ACK)
    match = _SWITCH_SET_TOPIC_PATTERN.fullmatch(topic)
    if match is not None:
        return ParsedTopic(kind=TopicKind.SWITCH_SET, switch_id=match.group('switch_id'))
    raise ValueError('unsupported MQTT topic for switch contract')