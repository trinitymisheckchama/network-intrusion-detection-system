# INIDMS Flask frontend

The Flask frontend serves a local dashboard for the Spring Boot API. It displays
the 50 newest events and lets you submit an event through the API; it does not
connect directly to the database.

## Run

Start the Java API first (see the project setup instructions), then from the
repository root install the frontend dependency and start Flask:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r frontend/requirements.txt
python -m frontend.app
```

Open <http://127.0.0.1:5000>. By default, Flask calls the Java API at
`http://127.0.0.1:8080`. Set `INIDMS_API_URL` to override the API base URL or
`FLASK_PORT` to change the frontend port. Set `FLASK_SECRET_KEY` to a stable,
private value when deploying beyond local development.

Both servers bind to loopback by default. Keep them on trusted interfaces and
add authentication and authorization before exposing the application to a LAN.
