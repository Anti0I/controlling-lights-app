from __future__ import annotations
import logging
import signal
import time
from datetime import datetime, timezone
from typing import Any
import paho.mqtt.client as mqtt
from shared.models import RegisterAck, RegisterRequest, SwitchSetCommand, SwitchState
from shared.mqtt_topics import REGISTER_REQUEST_TOPIC, TopicKind, build_register_ack_topic, parse_contract_topic
from simulator.settings import SimulatorSettings, get_settings
logger = logging.getLogger(__name__)
_switches: dict[str, dict[str, Any]] = {}

def _log_switch_table() -> None:
    if not _switches:
        logger.info('No switches registered yet')
        return
    logger.info('SIMULATED SWITCHES:')
    for sid, info in _switches.items():
        short_id = sid[:30] + '..' if len(sid) > 32 else sid.ljust(32)
        state = info['state'].ljust(8)
        name = info['name'][:15].ljust(15)
        logger.info('Switch ID: %s | State: %s | Name: %s', short_id, state, name)

def on_connect(client: mqtt.Client, userdata: Any, flags: mqtt.ConnectFlags, reason_code: mqtt.ReasonCode, properties: mqtt.Properties | None) -> None:
    if reason_code == 0:
        logger.info('Simulator connected to MQTT broker')
        settings: SimulatorSettings = userdata['settings']
        qos = settings.mqtt_qos
        client.subscribe(REGISTER_REQUEST_TOPIC, qos=qos)
        logger.info('  Subscribed to: %s (QoS=%s)', REGISTER_REQUEST_TOPIC, qos)
        set_topic = 'lighting/switch/+/set'
        client.subscribe(set_topic, qos=qos)
        logger.info('  Subscribed to: %s (QoS=%s)', set_topic, qos)
        logger.info('Simulator ready — waiting for commands...')
        _log_switch_table()
    else:
        logger.error('Connection failed with reason code %s', reason_code)

def on_disconnect(client: mqtt.Client, userdata: Any, flags: mqtt.DisconnectFlags, reason_code: mqtt.ReasonCode, properties: mqtt.Properties | None) -> None:
    if reason_code != 0:
        logger.warning('Unexpected disconnect (reason_code=%s), will auto-reconnect', reason_code)
    else:
        logger.info('Simulator disconnected from broker')

def on_message(client: mqtt.Client, userdata: Any, msg: mqtt.MQTTMessage) -> None:
    topic = msg.topic
    payload = msg.payload.decode('utf-8')
    logger.debug('Received on %s: %s', topic, payload)
    try:
        parsed = parse_contract_topic(topic)
    except ValueError:
        logger.warning('Unknown topic: %s', topic)
        return
    settings: SimulatorSettings = userdata['settings']
    if parsed.kind == TopicKind.REGISTER_REQUEST:
        _handle_register_request(client, settings, payload)
    elif parsed.kind == TopicKind.SWITCH_SET:
        _handle_switch_set(client, settings, payload, parsed.switch_id)
    else:
        logger.warning('Unhandled topic kind: %s', parsed.kind)

def _handle_register_request(client: mqtt.Client, settings: SimulatorSettings, payload: str) -> None:
    try:
        request = RegisterRequest.model_validate_json(payload)
    except Exception:
        logger.exception('Failed to parse registration request: %s', payload)
        return
    logger.info('--- REGISTRATION REQUEST ---')
    logger.info('request_id : %s', request.request_id)
    logger.info('switch_id  : %s', request.switch_id)
    logger.info('name       : %s', request.name)
    _switches[request.switch_id] = {'name': request.name, 'state': SwitchState.OFF.value, 'registered_at': datetime.now(timezone.utc).isoformat()}
    delay_s = settings.simulator_ack_delay_ms / 1000.0
    if delay_s > 0:
        time.sleep(delay_s)
    ack = RegisterAck(request_id=request.request_id, switch_id=request.switch_id, accepted=True)
    ack_topic = build_register_ack_topic()
    ack_payload = ack.model_dump_json()
    client.publish(ack_topic, payload=ack_payload, qos=settings.mqtt_qos)
    logger.info('--- REGISTRATION ACK sent -> accepted=True ---')
    _log_switch_table()

def _handle_switch_set(client: mqtt.Client, settings: SimulatorSettings, payload: str, switch_id: str | None) -> None:
    try:
        command = SwitchSetCommand.model_validate_json(payload)
    except Exception:
        logger.exception('Failed to parse switch set command: %s', payload)
        return
    sid = command.switch_id
    new_state = command.state.value
    logger.info('--- SWITCH SET COMMAND ---')
    if sid in _switches:
        old_state = _switches[sid]['state']
        _switches[sid]['state'] = new_state
        if new_state == SwitchState.ON.value:
            logger.info('LIGHT ON')
        else:
            logger.info('LIGHT OFF')
        logger.info('switch_id  : %s', sid)
        logger.info('name       : %s', _switches[sid]['name'])
        logger.info('old state  : %s', old_state)
        logger.info('new state  : %s', new_state)
    else:
        logger.warning('Command for unregistered switch: %s', sid)
        logger.info('Ignoring command. Switch must be registered first.')
    _log_switch_table()

def main() -> int:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s — %(message)s')
    settings = get_settings()
    if settings.simulator_dry_run:
        logger.info('Simulator running in DRY-RUN mode (no MQTT connection)')
        logger.info('Set SIMULATOR_DRY_RUN=false in .env to connect to the broker')
        return 0
    logger.info('Starting MQTT Light Switch Simulator...')
    logger.info('Connecting to %s:%s', settings.mqtt_host, settings.mqtt_port)
    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2, client_id='switch-simulator', protocol=mqtt.MQTTv311, userdata={'settings': settings})
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    running = True

    def signal_handler(sig: int, frame: Any) -> None:
        nonlocal running
        logger.info('Shutting down simulator...')
        running = False
    signal.signal(signal.SIGINT, signal_handler)
    try:
        client.connect(settings.mqtt_host, settings.mqtt_port, keepalive=settings.mqtt_keepalive)
        client.loop_start()
        while running:
            time.sleep(0.5)
    except KeyboardInterrupt:
        logger.info('Shutting down simulator...')
    except Exception:
        logger.exception('Simulator error')
        return 1
    finally:
        client.loop_stop()
        client.disconnect()
        logger.info('Simulator stopped')
    return 0

def cli() -> None:
    raise SystemExit(main())
if __name__ == '__main__':
    cli()