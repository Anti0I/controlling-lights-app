from __future__ import annotations
import logging
import threading
from datetime import datetime, timezone
from typing import Any
import paho.mqtt.client as mqtt
from app.config import Settings
from shared.models import RegisterAck, RegisterRequest, SwitchSetCommand, SwitchState
from shared.mqtt_topics import REGISTER_ACK_TOPIC, build_register_request_topic, build_switch_set_topic
logger = logging.getLogger(__name__)

class MQTTClient:

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2, client_id='webapp-backend', protocol=mqtt.MQTTv311)
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        self._client.on_disconnect = self._on_disconnect
        self._pending_acks: dict[str, tuple[threading.Event, dict[str, Any]]] = {}
        self._lock = threading.Lock()

    def start(self) -> None:
        logger.info('MQTT client connecting to %s:%s', self.settings.mqtt_host, self.settings.mqtt_port)
        self._client.connect(self.settings.mqtt_host, self.settings.mqtt_port, keepalive=self.settings.mqtt_keepalive)
        self._client.loop_start()

    def stop(self) -> None:
        logger.info('MQTT client disconnecting')
        self._client.loop_stop()
        self._client.disconnect()

    def _on_connect(self, client: mqtt.Client, userdata: Any, flags: mqtt.ConnectFlags, reason_code: mqtt.ReasonCode, properties: mqtt.Properties | None) -> None:
        if reason_code == 0:
            logger.info('MQTT connected successfully')
            client.subscribe(REGISTER_ACK_TOPIC, qos=self.settings.mqtt_qos)
            logger.info('Subscribed to %s', REGISTER_ACK_TOPIC)
        else:
            logger.error('MQTT connection failed with reason code %s', reason_code)

    def _on_disconnect(self, client: mqtt.Client, userdata: Any, flags: mqtt.DisconnectFlags, reason_code: mqtt.ReasonCode, properties: mqtt.Properties | None) -> None:
        if reason_code != 0:
            logger.warning('MQTT unexpected disconnect (reason_code=%s)', reason_code)

    def _on_message(self, client: mqtt.Client, userdata: Any, msg: mqtt.MQTTMessage) -> None:
        logger.debug('MQTT received on %s: %s', msg.topic, msg.payload.decode())
        if msg.topic == REGISTER_ACK_TOPIC:
            self._handle_register_ack(msg)

    def _handle_register_ack(self, msg: mqtt.MQTTMessage) -> None:
        try:
            ack = RegisterAck.model_validate_json(msg.payload)
            logger.info('Registration ACK received: request_id=%s switch_id=%s accepted=%s', ack.request_id, ack.switch_id, ack.accepted)
            with self._lock:
                pending = self._pending_acks.get(ack.request_id)
                if pending is not None:
                    event, result = pending
                    result['ack'] = ack
                    event.set()
                else:
                    logger.warning('No pending request for request_id=%s', ack.request_id)
        except Exception:
            logger.exception('Failed to parse registration ACK: %s', msg.payload)

    def publish_register_request(self, request_id: str, switch_id: str, name: str) -> None:
        request = RegisterRequest(request_id=request_id, switch_id=switch_id, name=name)
        topic = build_register_request_topic()
        payload = request.model_dump_json()
        logger.info('Publishing registration request to %s: %s', topic, payload)
        result = self._client.publish(topic, payload=payload, qos=self.settings.mqtt_qos)
        result.wait_for_publish(timeout=5.0)

    def request_register_with_ack(self, request_id: str, switch_id: str, name: str, timeout: float | None=None) -> RegisterAck | None:
        if timeout is None:
            timeout = self.settings.registration_ack_timeout_seconds
        event = threading.Event()
        result: dict[str, Any] = {}
        with self._lock:
            self._pending_acks[request_id] = (event, result)
        try:
            self.publish_register_request(request_id=request_id, switch_id=switch_id, name=name)
            received = event.wait(timeout=timeout)
            if received:
                return result.get('ack')
            logger.warning('Timeout waiting for registration ACK (request_id=%s)', request_id)
            return None
        finally:
            with self._lock:
                self._pending_acks.pop(request_id, None)

    def publish_switch_command(self, switch_id: str, state: SwitchState) -> None:
        command = SwitchSetCommand(switch_id=switch_id, state=state, sent_at=datetime.now(timezone.utc))
        topic = build_switch_set_topic(switch_id)
        payload = command.model_dump_json()
        logger.info('Publishing command to %s: %s', topic, payload)
        result = self._client.publish(topic, payload=payload, qos=self.settings.mqtt_qos)
        result.wait_for_publish(timeout=5.0)

    def wait_for_register_ack(self, request_id: str, timeout: float | None=None) -> RegisterAck | None:
        if timeout is None:
            timeout = self.settings.registration_ack_timeout_seconds
        event = threading.Event()
        result: dict[str, Any] = {}
        with self._lock:
            self._pending_acks[request_id] = (event, result)
        try:
            received = event.wait(timeout=timeout)
            if received:
                return result.get('ack')
            logger.warning('Timeout waiting for registration ACK (request_id=%s)', request_id)
            return None
        finally:
            with self._lock:
                self._pending_acks.pop(request_id, None)
_mqtt_client: MQTTClient | None = None

def get_mqtt_client() -> MQTTClient:
    if _mqtt_client is None:
        raise RuntimeError('MQTT client not initialized. Call init_mqtt_client() first.')
    return _mqtt_client

def init_mqtt_client(settings: Settings) -> MQTTClient:
    global _mqtt_client
    _mqtt_client = MQTTClient(settings)
    _mqtt_client.start()
    return _mqtt_client

def stop_mqtt_client() -> None:
    global _mqtt_client
    if _mqtt_client is not None:
        _mqtt_client.stop()
        _mqtt_client = None