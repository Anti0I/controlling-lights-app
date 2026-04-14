from __future__ import annotations
import logging
from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI
from app.database import init_db
from shared.models import HealthResponse
from webapp.app.config import get_settings
from webapp.app.mqtt_client import init_mqtt_client, stop_mqtt_client
from webapp.app.router import router as switches_router
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    init_db()
    logger.info('Database initialized')
    init_mqtt_client(settings)
    logger.info('Webapp started — api=%s:%s mqtt=%s:%s qos=%s', settings.api_host, settings.api_port, settings.mqtt_host, settings.mqtt_port, settings.mqtt_qos)
    yield
    stop_mqtt_client()
    logger.info('Webapp stopped')

def create_app() -> FastAPI:
    application = FastAPI(title='MQTT Light Switch Manager', description='FastAPI service for managing light switches via MQTT', version='0.1.0', lifespan=lifespan)

    @application.get('/health', response_model=HealthResponse, tags=['health'])
    async def health() -> HealthResponse:
        return HealthResponse(status='ok')
    application.include_router(switches_router)
    return application
app = create_app()

def run() -> None:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s — %(message)s')
    settings = get_settings()
    uvicorn.run('webapp.app.main:app', host=settings.api_host, port=settings.api_port, reload=False)
if __name__ == '__main__':
    run()