# INIDMS

INIDMS is a portfolio project for monitoring an authorized local network and recording
potentially suspicious traffic. This milestone provides the Java event API and MySQL
storage layer. It does not capture packets or decide whether traffic is malicious yet.

## Requirements

- Java 25 (latest LTS)
- Maven 3.9+
- Docker Compose (for the included local MySQL service)

## Start the database

Copy `.env.example` to `.env`, replace both example passwords, and start MySQL:

```sh
cp .env.example .env
docker compose up -d mysql
```

The database port is bound to `127.0.0.1` only. The `.env` file is ignored by Git.

## Run the API

Export the application database settings from `.env`, then start Spring Boot:

```sh
set -a
. ./.env
set +a
mvn spring-boot:run
```

The API listens on `127.0.0.1:8080` by default. Override `INIDMS_SERVER_ADDRESS`
only when you intentionally want to listen on another interface; add authentication
and agent authorization before exposing it to a LAN.

### Submit an event

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

The response includes the generated database ID and a server timestamp when
`capturedAt` is omitted. Valid protocol values are `TCP`, `UDP`, `ICMP`, and `OTHER`.

### List events

```sh
curl 'http://127.0.0.1:8080/api/events?page=0&size=50'
```

Pages are zero-based and the requested page size is capped at 100. Request fields
are validated; source and destination IP strings are length-checked but are not yet
verified as actual IP addresses.

## Verify

Run the API tests with:

```sh
mvn test
```

Tests use an in-memory H2 database and do not require MySQL or Docker.
