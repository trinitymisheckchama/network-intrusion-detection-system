import unittest
from unittest.mock import patch

from frontend.app import BackendError, create_app


class FlaskFrontendTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app("http://java-api.test")
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def csrf_token(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        with self.client.session_transaction() as session:
            return session["csrf_token"]

    @patch("frontend.app.api_request")
    def test_dashboard_lists_events_from_backend(self, api_request):
        api_request.return_value = [{
            "id": 4,
            "sourceIp": "192.168.1.5",
            "sourcePort": 5050,
            "destinationIp": "192.168.1.8",
            "destinationPort": 443,
            "protocol": "TCP",
            "packetSize": 128,
            "eventType": "CONNECTION",
            "capturedAt": "2026-10-31T12:00:00Z",
        }]

        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"CONNECTION", response.data)
        self.assertIn(b"192.168.1.5:5050", response.data)
        self.assertEqual(api_request.call_args.args[1], "GET")

    @patch("frontend.app.api_request")
    def test_valid_form_posts_event_then_refreshes_list(self, api_request):
        token = self.csrf_token()
        api_request.reset_mock()
        api_request.side_effect = [
            {"id": 9},
            [{
                "id": 9,
                "sourceIp": "192.168.1.5",
                "sourcePort": 5050,
                "destinationIp": "192.168.1.8",
                "destinationPort": 443,
                "protocol": "TCP",
                "packetSize": 128,
                "eventType": "CONNECTION",
                "capturedAt": "2026-10-31T12:00:00Z",
            }],
        ]

        response = self.client.post(
            "/events",
            data={
                "csrf_token": token,
                "sourceIp": "192.168.1.5",
                "sourcePort": "5050",
                "destinationIp": "192.168.1.8",
                "destinationPort": "443",
                "protocol": "TCP",
                "packetSize": "128",
                "eventType": "CONNECTION",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Event #9 was submitted", response.data)
        self.assertEqual(api_request.call_count, 2)
        self.assertEqual(api_request.call_args_list[0].args[1], "POST")
        self.assertEqual(api_request.call_args_list[0].args[3]["sourcePort"], 5050)

    @patch("frontend.app.api_request")
    def test_rejects_invalid_input_without_calling_backend(self, api_request):
        token = self.csrf_token()
        api_request.reset_mock()

        response = self.client.post(
            "/events",
            data={
                "csrf_token": token,
                "sourceIp": "192.168.1.5",
                "destinationIp": "192.168.1.8",
                "protocol": "INVALID",
                "packetSize": "not-a-number",
                "eventType": "bad event",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn(b"Select a valid protocol", response.data)
        self.assertIn(b"Packet size must be a whole number", response.data)
        self.assertTrue(
            all(call.args[1] == "GET" for call in api_request.call_args_list)
        )

    @patch("frontend.app.api_request")
    def test_shows_backend_error_on_dashboard(self, api_request):
        api_request.side_effect = BackendError("Java API is unavailable.")

        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"API unavailable", response.data)
        self.assertIn(b"Java API is unavailable", response.data)

    def test_rejects_missing_csrf_token(self):
        response = self.client.post("/events", data={})

        self.assertEqual(response.status_code, 400)
        self.assertIn(b"Your form session expired", response.data)


if __name__ == "__main__":
    unittest.main()
