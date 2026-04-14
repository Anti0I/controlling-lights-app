from simulator.settings import get_settings

def test_simulator_settings_parse_bool_env(monkeypatch) -> None:
    monkeypatch.setenv('SIMULATOR_DRY_RUN', 'false')
    monkeypatch.setenv('MQTT_QOS', '1')
    get_settings.cache_clear()
    settings = get_settings()
    assert settings.simulator_dry_run is False
    assert settings.mqtt_qos == 1
    get_settings.cache_clear()