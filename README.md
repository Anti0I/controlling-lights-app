# README-AI-GENERATED
# MQTT Light Switch Manager

Projekt symuluje komunikacje aplikacji webowej z prostymi urzadzeniami (wlaczniki swiatla) przez MQTT.

## Co realizuje zadanie

### FastAPI (webapp)
- Rejestracja nowego wlacznika (`POST /switches`) z nazwa.
- Wlaczniki sa identyfikowane przez UUID.
- Wlaczniki sa zapisywane do bazy dopiero po ACK z symulatora przez MQTT.
- Zmiana stanu wlacznika (`POST /switches/{id}/on`, `POST /switches/{id}/off`).
- Zapis i odczyt statystyk czasu dzialania oswietlenia (`GET /switches/{id}/stats`).

### Symulator (MQTT listener)
- Odbiera rejestracje (`lighting/switch/register/request`) i odsyla ACK (`lighting/switch/register/ack`).
- Odbiera komendy ON/OFF (`lighting/switch/{switch_id}/set`) i loguje zmiane stanu.

## MQTT kontrakt

- `lighting/switch/register/request` - backend -> symulator
- `lighting/switch/register/ack` - symulator -> backend
- `lighting/switch/{switch_id}/set` - backend -> symulator

## Struktura

- `webapp/app/` - FastAPI (router + service + klient MQTT)
- `simulator/` - symulator urzadzenia
- `app/` - modele SQLAlchemy, repository, konfiguracja
- `shared/` - wspolne modele i tematy MQTT
- `tests/` - testy

## Uruchomienie lokalne

1. Instalacja zaleznosci:
   - `pip install -e ".[dev]"`
2. Konfiguracja:
   - skopiuj `.env.example` do `.env`
3. Start brokera MQTT (Docker):
   - `docker compose up -d mosquitto`
4. Start symulatora:
   - `python -m simulator.main`
5. Start webapp:
   - `python -m webapp.app.main`

## Testy i jakosc

- Testy: `python -m pytest -q`
- Lint: `ruff check .`
- CI (GitHub Actions): workflow uruchamia `ruff` i `pytest` na push/pull request.
