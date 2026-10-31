import hmac
import json
import os
import re
import secrets
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from flask import Flask, render_template, request, session


PROTOCOLS = ("TCP", "UDP", "ICMP", "OTHER")
EVENT_TYPE_PATTERN = re.compile(r"[A-Z][A-Z0-9_]{0,63}")
EVENTS_PATH = "/api/events"


class BackendError(Exception):
    pass


def _error_detail(body):
    try:
        problem = json.loads(body)
    except json.JSONDecodeError:
        problem = None

    if isinstance(problem, dict):
        detail = problem.get("detail") or problem.get("title")
        if detail:
            return str(detail)
    return body.strip()[:500] or "The backend returned an empty error response."


def api_request(base_url, method, path, payload=None):
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"

    api_request = Request(
        f"{base_url.rstrip('/')}{path}",
        data=body,
        headers=headers,
        method=method,
    )
    try:
        with urlopen(api_request, timeout=5) as response:
            response_body = response.read().decode("utf-8")
    except HTTPError as error:
        response_body = error.read().decode("utf-8", errors="replace")
        raise BackendError(
            f"Backend rejected the request (HTTP {error.code}): "
            f"{_error_detail(response_body)}"
        ) from error
    except URLError as error:
        raise BackendError(
            "Could not reach the Java API. Check that the backend is running "
            "and that INIDMS_API_URL points to it."
        ) from error

    if not response_body:
        return None
    try:
        return json.loads(response_body)
    except json.JSONDecodeError as error:
        raise BackendError("The Java API returned an invalid JSON response.") from error


def _integer_field(form, name, label, minimum, maximum, errors, required=True):
    raw_value = form.get(name, "").strip()
    if not raw_value:
        if required:
            errors.append(f"{label} is required.")
        return None

    try:
        value = int(raw_value)
    except ValueError:
        errors.append(f"{label} must be a whole number.")
        return None

    if not minimum <= value <= maximum:
        errors.append(f"{label} must be between {minimum} and {maximum}.")
        return None
    return value


def _validate_event(form):
    errors = []
    source_ip = form.get("sourceIp", "").strip()
    destination_ip = form.get("destinationIp", "").strip()
    event_type = form.get("eventType", "").strip()
    protocol = form.get("protocol", "").strip()

    if not source_ip:
        errors.append("Source IP is required.")
    elif len(source_ip) > 45:
        errors.append("Source IP must be 45 characters or fewer.")

    if not destination_ip:
        errors.append("Destination IP is required.")
    elif len(destination_ip) > 45:
        errors.append("Destination IP must be 45 characters or fewer.")

    if protocol not in PROTOCOLS:
        errors.append("Select a valid protocol.")

    if not EVENT_TYPE_PATTERN.fullmatch(event_type):
        errors.append(
            "Event type must start with an uppercase letter and contain only "
            "uppercase letters, digits, or underscores (up to 64 characters)."
        )

    source_port = _integer_field(
        form, "sourcePort", "Source port", 0, 65535, errors, required=False
    )
    destination_port = _integer_field(
        form,
        "destinationPort",
        "Destination port",
        0,
        65535,
        errors,
        required=False,
    )
    packet_size = _integer_field(
        form, "packetSize", "Packet size", 0, 65535, errors
    )

    if errors:
        return None, errors

    return {
        "sourceIp": source_ip,
        "destinationIp": destination_ip,
        "sourcePort": source_port,
        "destinationPort": destination_port,
        "protocol": protocol,
        "packetSize": packet_size,
        "eventType": event_type,
    }, []


def create_app(api_base_url=None):
    app = Flask(__name__)
    app.secret_key = os.environ.get("FLASK_SECRET_KEY") or secrets.token_hex(32)
    app.config["API_BASE_URL"] = (
        api_base_url or os.environ.get("INIDMS_API_URL", "http://127.0.0.1:8080")
    ).rstrip("/")
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

    def get_events():
        events = api_request(
            app.config["API_BASE_URL"],
            "GET",
            f"{EVENTS_PATH}?{urlencode({'page': 0, 'size': 50})}",
        )
        if not isinstance(events, list):
            raise BackendError("The Java API returned an unexpected event list.")
        return events

    def render_dashboard(
        events=None,
        load_error=None,
        errors=None,
        success=None,
        form_data=None,
        status=200,
    ):
        if events is None and load_error is None:
            try:
                events = get_events()
            except BackendError as error:
                load_error = str(error)

        if "csrf_token" not in session:
            session["csrf_token"] = secrets.token_urlsafe(32)

        return (
            render_template(
                "index.html",
                events=events or [],
                load_error=load_error,
                errors=errors or [],
                success=success,
                form_data=form_data or {},
                csrf_token=session["csrf_token"],
            ),
            status,
        )

    @app.get("/")
    def index():
        return render_dashboard()

    @app.post("/events")
    def create_event():
        expected_token = session.get("csrf_token", "")
        submitted_token = request.form.get("csrf_token", "")
        if not expected_token or not hmac.compare_digest(
            expected_token, submitted_token
        ):
            return render_dashboard(
                errors=["Your form session expired. Reload the page and try again."],
                form_data=request.form,
                status=400,
            )

        payload, errors = _validate_event(request.form)
        if errors:
            return render_dashboard(
                errors=errors,
                form_data=request.form,
                status=400,
            )

        try:
            created_event = api_request(
                app.config["API_BASE_URL"], "POST", EVENTS_PATH, payload
            )
            if not isinstance(created_event, dict):
                raise BackendError("The Java API returned an unexpected event.")
        except BackendError as error:
            return render_dashboard(
                errors=[str(error)],
                form_data=request.form,
                status=502,
            )

        try:
            events = get_events()
        except BackendError as error:
            return render_dashboard(
                load_error=str(error),
                success=f"Event #{created_event.get('id', '')} was submitted.",
            )

        return render_dashboard(
            events=events,
            success=f"Event #{created_event.get('id', '')} was submitted.",
        )

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("FLASK_PORT", "5000")))
