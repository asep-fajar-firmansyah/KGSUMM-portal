import unittest
from unittest.mock import patch

from app import create_app


class PortalTests(unittest.TestCase):
    def setUp(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            self.app = create_app()
        self.client = self.app.test_client()

    def test_default_links(self) -> None:
        response = self.client.get("/", base_url="http://localhost:8080")
        self.assertEqual(response.status_code, 200)
        page = response.get_data(as_text=True)
        for name, slug in (("ToT4ES", "tot4es"), ("Human Evaluation", "evaluation"), ("Synthetic Dataset", "dataset")):
            self.assertIn(name, page)
            self.assertIn(f'href="/workspace/{slug}/"', page)
        self.assertNotIn('href="http://localhost:', page)

    def test_remote_hostname_and_https(self) -> None:
        page = self.client.get("/", base_url="https://research.example:8080").get_data(as_text=True)
        for slug in ("tot4es", "evaluation", "dataset"):
            self.assertIn(f'href="/workspace/{slug}/"', page)
        self.assertNotIn('href="https://research.example:', page)

    def test_ipv6_links(self) -> None:
        page = self.client.get("/", base_url="http://[::1]:8080").get_data(as_text=True)
        self.assertIn('href="/workspace/tot4es/"', page)

    def test_configuration_overrides(self) -> None:
        with patch.dict("os.environ", {"TOT4ES_PORT": "9000"}):
            app = create_app()
        page = app.test_client().get("/", base_url="https://research.example").get_data(as_text=True)
        self.assertIn('PORT 9000', page)
        self.assertIn('href="/workspace/tot4es/"', page)

    def test_invalid_configuration(self) -> None:
        for settings in ({"TOT4ES_PORT": "70000"}, {"HUMAN_EVALUATION_PORT": "0"}):
            with self.subTest(settings=settings), patch.dict("os.environ", settings):
                with self.assertRaises(ValueError):
                    create_app()

    def test_framed_services_use_same_origin(self) -> None:
        for slug in ("tot4es", "evaluation", "dataset"):
            response = self.client.get(f"/workspace/{slug}/")
            self.assertEqual(response.status_code, 200)
            self.assertIn(f'src="/services/{slug}/"', response.get_data(as_text=True))
            self.assertNotIn("127.0.0.1", response.get_data(as_text=True))

    def test_unknown_service_is_not_forwarded(self) -> None:
        self.assertEqual(self.client.get("/workspace/unknown/").status_code, 404)
        self.assertEqual(self.client.get("/services/unknown/").status_code, 404)

    def test_without_proxy_returns_explanatory_error(self) -> None:
        response = self.client.get("/services/evaluation/")
        self.assertEqual(response.status_code, 503)
        self.assertIn("reverse proxy", response.get_data(as_text=True))

    def test_stylesheet(self) -> None:
        with self.client.get("/static/style.css") as response:
            self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()