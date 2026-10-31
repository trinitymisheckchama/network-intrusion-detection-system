import queue
import threading
import unittest
from unittest.mock import Mock
from urllib.error import URLError

from scapy.all import Ether, ICMP, ICMPv6EchoRequest, IP, IPv6, Raw, TCP, UDP

from monitoring.agent import STOP, _delivery_worker, packet_to_event, run_monitor


class PacketMetadataTest(unittest.TestCase):
    def test_extracts_tcp_fields_without_including_payload(self):
        packet = (
            Ether()
            / IP(src="192.168.1.5", dst="192.168.1.10")
            / TCP(sport=50000, dport=443)
            / Raw(load=b"private payload")
        )

        event = packet_to_event(packet, "2026-10-31T12:00:00+00:00")

        self.assertEqual(event["sourceIp"], "192.168.1.5")
        self.assertEqual(event["destinationIp"], "192.168.1.10")
        self.assertEqual(event["sourcePort"], 50000)
        self.assertEqual(event["destinationPort"], 443)
        self.assertEqual(event["protocol"], "TCP")
        self.assertEqual(event["eventType"], "CAPTURED_TCP")
        self.assertEqual(event["packetSize"], len(packet))
        self.assertEqual(event["capturedAt"], "2026-10-31T12:00:00Z")
        self.assertNotIn("payload", event)
        self.assertNotIn(b"private payload", repr(event).encode())

    def test_extracts_udp_and_icmp(self):
        udp_event = packet_to_event(
            IP(src="10.0.0.1", dst="10.0.0.2") / UDP(sport=53, dport=53000)
        )
        icmp_event = packet_to_event(
            IP(src="10.0.0.1", dst="10.0.0.2") / ICMP()
        )

        self.assertEqual((udp_event["protocol"], udp_event["sourcePort"]), ("UDP", 53))
        self.assertEqual(udp_event["destinationPort"], 53000)
        self.assertEqual(icmp_event["protocol"], "ICMP")
        self.assertIsNone(icmp_event["sourcePort"])
        self.assertIsNone(icmp_event["destinationPort"])

    def test_extracts_ipv6_addresses_and_icmpv6(self):
        packet = (
            IPv6(src="2001:db8::1", dst="2001:db8::2")
            / ICMPv6EchoRequest()
        )

        event = packet_to_event(packet)

        self.assertEqual(event["sourceIp"], "2001:db8::1")
        self.assertEqual(event["destinationIp"], "2001:db8::2")
        self.assertEqual(event["protocol"], "ICMP")

    def test_ignores_non_ip_and_unsupported_ip_protocols(self):
        self.assertIsNone(packet_to_event(Ether() / Raw(load=b"frame")))
        self.assertIsNone(packet_to_event(IP() / Raw(load=b"other protocol")))


class DeliveryResilienceTest(unittest.TestCase):
    def test_delivery_worker_continues_after_send_failure(self):
        events = queue.Queue()
        events.put({"id": 1})
        events.put({"id": 2})
        events.put(STOP)
        sender = Mock(side_effect=[URLError("backend offline"), True])

        _delivery_worker(events, "http://api.test", sender)

        self.assertEqual(sender.call_count, 2)
        self.assertEqual(events.unfinished_tasks, 0)

    def test_capture_error_is_logged_and_monitor_can_stop_cleanly(self):
        stopping = threading.Event()

        def capture_failure(**kwargs):
            stopping.set()
            raise OSError("capture device unavailable")

        capture = Mock(side_effect=capture_failure)

        run_monitor(
            "test-interface",
            "http://api.test",
            stop_event=stopping,
            capture=capture,
            sender=Mock(return_value=True),
        )

        capture.assert_called_once()


if __name__ == "__main__":
    unittest.main()