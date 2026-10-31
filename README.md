# INIDMS

INIDMS is a portfolio project for monitoring an authorized local network and
recording potentially suspicious traffic. It includes a Java Spring Boot API,
MySQL storage, and a Python Flask dashboard. This milestone stores and displays
events submitted to the API; it does not capture packets or determine whether
traffic is malicious.

## Requirements

- Java 25 (LTS)
- Python 3.10+
- Docker Compose (for the included local MySQL service)

The Maven wrapper (`mvnw`) is included, so a separate Maven installation is not
required.

## Configure and start MySQL

From the repository root, copy the example environment file and replace the
example passwords with strong local values:

```sh
cp .env.example .env
docker compose up -d mysql
```

The MySQL port is bound to `127.0.0.1`. The `.env` file is ignored by Git; do not
commit real credentials.

## Run the Java backend

In a terminal from the repository root, load the database settings and start
Spring Boot:

```sh
set -a
. ./.env
set +a
./mvnw spring-boot:run
```

The API listens on `http://127.0.0.1:8080` by default. Override
`INIDMS_SERVER_ADDRESS` or `INIDMS_SERVER_PORT` only when you intentionally want
to change its bind address or port.

### API endpoints

- `GET /api/events?page=0&size=50` lists events, newest first. Pages are
  zero-based; page size must be between 1 and 100.
- `POST /api/events` creates an event and returns HTTP 201.

Example request:

```sh
curl -X POST http://127.0.0.1:8080/api/events \
  -H 'Content-Type: application/json' \
  -d '{
    "sourceIp": "192.168.1.105",
    "destinationIp": "192.168.1.10",
    "sourcePort": 45678,
    "destinationPort": 22,
    "protocol": "TCP",
    "packetSize": 120,
    "eventType": "SUSPICIOUS_CONNECTION"
  }'
```

Valid protocols are `TCP`, `UDP`, `ICMP`, and `OTHER`. Ports and packet size
must be between 0 and 65535. Source and destination IP fields are length-checked
but are not yet verified as actual IP addresses. If `capturedAt` is omitted, the
server supplies the timestamp.

## Run the Flask frontend

Keep the Java backend running. In a second terminal at the repository root,
create a virtual environment, install Flask, and start the dashboard:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r frontend/requirements.txt
python -m frontend.app
```

Open <http://127.0.0.1:5000>. The dashboard displays the latest 50 events and
submits new events through the Java API. Flask does not connect directly to
MySQL.

By default, the frontend calls `http://127.0.0.1:8080`. Configure
`INIDMS_API_URL` to use another API base URL or `FLASK_PORT` to change the
frontend port. Set `FLASK_SECRET_KEY` to a stable, private value when running
outside local development.

Both services bind to loopback by default. Add authentication and authorization
before exposing the application to a LAN.

## Tests

Run the backend tests from the repository root:

```sh
./mvnw test
```

The Java tests use an in-memory H2 database and do not require MySQL or Docker.
Run the frontend tests with the virtual environment activated:

```sh
python -m unittest frontend.test_app -v
```