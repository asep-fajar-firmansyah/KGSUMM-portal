import os
from urllib.parse import urlsplit

from flask import Flask, abort, render_template, request, url_for


SERVICES = [
    {"slug": "tot4es", "name": "ToT4ES", "category": "SUMMARIZATION", "icon": "network", "key": "TOT4ES_PORT", "color": "green"},
    {"slug": "evaluation", "name": "Human Evaluation", "category": "ASSESSMENT", "icon": "users", "key": "HUMAN_EVALUATION_PORT", "color": "blue"},
    {"slug": "dataset", "name": "Synthetic Dataset", "category": "DATA", "icon": "database", "key": "SYNTHETIC_DATASET_PORT", "color": "rose"},
]


def configured_port(name: str, default: int) -> int:
    port = int(os.environ.get(name, default))
    if not 1 <= port <= 65535:
        raise ValueError(f"{name} must be between 1 and 65535")
    return port


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_mapping(
        TOT4ES_PORT=configured_port("TOT4ES_PORT", 5000),
        HUMAN_EVALUATION_PORT=configured_port("HUMAN_EVALUATION_PORT", 8011),
        SYNTHETIC_DATASET_PORT=configured_port("SYNTHETIC_DATASET_PORT", 8022),
    )

    @app.get("/")
    def index() -> str:
        hostname = urlsplit(request.host_url).hostname
        if hostname is None:
            raise ValueError("Request has no hostname")
        services = [dict(service) for service in SERVICES]
        for service in services:
            service["port"] = app.config[service["key"]]
            service["url"] = url_for("workspace", slug=service["slug"])
        return render_template("index.html", services=services, hostname=hostname)

    @app.get("/workspace/<slug>/")
    def workspace(slug: str) -> str:
        service = next((item for item in SERVICES if item["slug"] == slug), None)
        if service is None:
            abort(404)
        return render_template("workspace.html", service=service, frame_url=f"/services/{slug}/")

    @app.get("/services/<slug>/", defaults={"path": ""})
    @app.get("/services/<slug>/<path:path>")
    def proxy_not_configured(slug: str, path: str) -> tuple[str, int]:
        if not any(service["slug"] == slug for service in SERVICES):
            abort(404)
        return render_template("unavailable.html"), 503

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=configured_port("PORT", 8081))