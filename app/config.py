from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = 'MQTT FastAPI Demo'
    api_host: str = '127.0.0.1'
    api_port: int = Field(default=8000, ge=1, le=65535)
    database_url: str = 'sqlite:///./switches.db'
    mqtt_host: str = '127.0.0.1'
    mqtt_port: int = 1883
    mqtt_qos: int = Field(default=1, ge=0, le=2)
    mqtt_keepalive: int = 60
    mqtt_client_id: str = 'simulator-bootstrap'
    mqtt_topic: str = 'devices/bootstrap'
    mqtt_topic_prefix: str = 'devices'
    simulator_dry_run: bool = True
    simulator_ack_delay_ms: int = 50
    registration_ack_timeout_seconds: float = 3.0
    command_ack_timeout_seconds: float = 3.0
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    def switch_command_topic(self, switch_id: str) -> str:
        return f'{self.mqtt_topic_prefix}/{switch_id}/command'

    def switch_ack_topic(self, switch_id: str) -> str:
        return f'{self.mqtt_topic_prefix}/{switch_id}/ack'

@lru_cache
def get_settings() -> Settings:
    return Settings()