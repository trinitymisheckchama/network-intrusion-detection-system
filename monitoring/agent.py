
"""Capture packet metadata on one explicitly selected local interface."""

import argparse
import json
import logging
import os
import queue
import threading
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from scapy.all import ICMP, IP, IPv6, TCP, UDP, conf, sniff


LOGGER = logging.getLogger("inidms.monitor")

EVENTS_PATH = "/api/events"
MAX_PACKET_SIZE = 65535
QUEUE_CAPACITY = 1000
STOP = object()


def available_interfaces():
    """Return the interface objects Scapy can use for capture."""
    return list(conf.ifaces.values())


def _interface_name(interface):
    return str(getattr(interface, "name", interface))


def packet_to_event(packet, captured_at=None):
    """Convert an IP packet to metadata without retaining its payload."""

    if IP in packet:
        ip_packet = packet[IP]
    elif IPv6 in packet:
        ip_packet = packet[IPv6]
    else:
        return None

    source_port = None
    destination_port = None

    if TCP in packet:
        protocol = "TCP"
        source_port = int(packet[TCP].sport)
        destination_port = int(packet[TCP].dport)

    elif UDP in packet:
        protocol = "UDP"
        source_port = int(packet[UDP].sport)
        destination_port = int(packet[UDP].dport)

    elif ICMP in packet or any(
        layer.__name__.startswith("ICMPv6")
        for layer in packet.layers()
    ):
        protocol = "ICMP"

    else:
        return None

    timestamp = captured_at or datetime.now(timezone.utc).isoformat()

    if timestamp.endswith("+00:00"):
        timestamp = f"{timestamp[:-6]}Z"

    return {
        "sourceIp": str(ip_packet.src),
        "destinationIp": str(ip_packet.dst),
        "sourcePort": source_port,
        "destinationPort": destination_port,
        "protocol": protocol,
        "packetSize": min(len(packet), MAX_PACKET_SIZE),
        "eventType": f"CAPTURED_{protocol}",
        "capturedAt": timestamp,
    }


def send_event(api_url, event, timeout=5):
    """Send one network event to the Java backend."""

    request = Request(
        f"{api_url.rstrip('/')}{EVENTS_PATH}",
        data=json.dumps(event).encode("utf-8"),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    with urlopen(request, timeout=timeout) as response:
        return 200 <= response.status < 300


def _delivery_worker(events, api_url, sender):
    """Process queued events and deliver them to the backend."""

    while True:
        event = events.get()

        try:
            if event is STOP:
                return

            try:
                if sender(api_url, event):
                    LOGGER.info(
                        "EVENT SENT SUCCESSFULLY | %s -> %s | Protocol: %s",
                        event["sourceIp"],
                        event["destinationIp"],
                        event["protocol"],
                    )
                else:
                    LOGGER.warning(
                        "API rejected a captured event; continuing."
                    )

            except (
                HTTPError,
                URLError,
                TimeoutError,
                OSError,
                ValueError,
            ) as error:
                LOGGER.warning(
                    "Could not send captured event: %s",
                    error,
                )

            except Exception:
                LOGGER.exception(
                    "Unexpected event delivery error; continuing."
                )

        finally:
            events.task_done()


def run_monitor(
    interface,
    api_url,
    retry_seconds=5,
    stop_event=None,
    capture=sniff,
    sender=send_event,
):
    """Capture packets and queue metadata for API delivery."""

    stopping = stop_event or threading.Event()
    events = queue.Queue(maxsize=QUEUE_CAPACITY)

    worker = threading.Thread(
        target=_delivery_worker,
        args=(events, api_url, sender),
        name="inidms-event-sender",
        daemon=True,
    )

    worker.start()

    def handle_packet(packet):
        try:
            event = packet_to_event(packet)

            if event is None:
                return

            events.put_nowait(event)

            LOGGER.info(
                "PACKET CAPTURED | %s -> %s | Protocol: %s | "
                "Destination port: %s | Size: %s bytes",
                event["sourceIp"],
                event["destinationIp"],
                event["protocol"],
                event["destinationPort"],
                event["packetSize"],
            )

        except queue.Full:
            LOGGER.warning(
                "Event queue is full; dropping captured metadata."
            )

        except Exception:
            LOGGER.exception(
                "Could not process captured packet; continuing."
            )

    LOGGER.info(
        "Monitoring interface %s; packet payloads are not stored.",
        _interface_name(interface),
    )

    try:
        while not stopping.is_set():
            try:
                capture(
                    iface=interface,
                    prn=handle_packet,
                    store=False,
                    promisc=False,
                    filter="ip or ip6",
                    timeout=1,
                )

            except KeyboardInterrupt:
                raise

            except Exception as error:
                LOGGER.error(
                    "Capture error on %s: %s",
                    _interface_name(interface),
                    error,
                )
                stopping.wait(retry_seconds)

    finally:
        events.put(STOP)
        worker.join(timeout=10)

        if worker.is_alive():
            LOGGER.warning(
                "API sender is still shutting down."
            )


def _parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Capture TCP, UDP, and ICMP metadata "
            "on one local interface."
        )
    )

    parser.add_argument(
        "--interface",
        help="Interface name from --list-interfaces",
    )

    parser.add_argument(
        "--list-interfaces",
        action="store_true",
        help="Show available interfaces and exit",
    )

    parser.add_argument(
        "--api-url",
        default=os.environ.get(
            "INIDMS_API_URL",
            "http://127.0.0.1:8080",
        ),
        help="Java API base URL",
    )

    parser.add_argument(
        "--retry-seconds",
        type=float,
        default=5,
        help="Delay after capture errors",
    )

    args = parser.parse_args(argv)

    if args.retry_seconds < 0:
        parser.error("--retry-seconds must not be negative")

    return parser, args


def main(argv=None):
    parser, args = _parse_args(argv)

    interfaces = {
        _interface_name(interface): interface
        for interface in available_interfaces()
    }

    if args.list_interfaces:
        if not interfaces:
            print("No capture interfaces were found.")

        for name, interface in interfaces.items():
            description = getattr(interface, "description", "")
            addresses = getattr(interface, "ips", {})
            ipv4_addresses = ", ".join(
                addresses.get(4, [])
            ) or "no IPv4"

            print(
                f"{name} | {description} | {ipv4_addresses}"
            )

        return 0

    if not args.interface:
        parser.error(
            "Choose an interface with --interface "
            "or use --list-interfaces"
        )

    if args.interface not in interfaces:
        parser.error(
            f"Unknown interface {args.interface!r}; "
            "use --list-interfaces to see options"
        )

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    try:
        run_monitor(
            interfaces[args.interface],
            args.api_url,
            args.retry_seconds,
        )

    except KeyboardInterrupt:
        LOGGER.info("Monitoring stopped by user.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
