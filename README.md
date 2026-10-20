# KGSUMM Portal

A Python/Flask portal with four service boxes:

| Service | Default port |
| --- | --- |
| ToT4ES | 5000 |
| Human Evaluation | 8011 |
| Synthetic Dataset | 8022 |
| LLM-Walk | 8044 |

Each box opens a full-height iframe with a same-origin URL. Nginx accepts public
connections on port 8080 and forwards requests to private applications:

| Public path on port 8080 | Private upstream |
| --- | --- |
| `/` and `/workspace/.../` | Flask portal on `127.0.0.1:8081` |
| `/services/tot4es/` | `127.0.0.1:5000` |
| `/services/evaluation/` | `127.0.0.1:8011` |
| `/services/dataset/` | `127.0.0.1:8022` |
| `/services/llm-walk/` | `127.0.0.1:8044` |

Visitors never connect directly to a backend port. All applications must run on
the same server as Nginx (or update its upstream addresses). The portal does not
start the backend applications or check their availability.

## Run

Requires Python 3.10 or newer.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

Flask now listens on http://127.0.0.1:8081. This address is only for local portal
development: framed services return an explanatory 503 without Nginx.

On Debian/Ubuntu, creating a venv may require installing `python3-venv` first.

## Start The Public Gateway

Install Nginx using your system package manager. Start the three backend apps
bound to localhost, then start Flask as above. If the previous portal process is
still using port 8080, stop that task first and restart it with the updated code.

From the repository root, in a separate terminal:

```sh
nginx -p "$PWD/deploy/" -c nginx.conf -t
nginx -p "$PWD/deploy/" -c nginx.conf -g 'daemon off;'
```

Open http://127.0.0.1:8080 locally or `http://YOUR_SERVER:8080` remotely. Expose
only port 8080 through the firewall; keep 5000, 8011, 8022, and 8081 private.
The supplied standalone config can run without root on port 8080 and writes
temporary files and logs under `/tmp`. It is separate from the system Nginx
service; do not run both on port 8080. Stop it with Ctrl+C.

The gateway forwards HTTP methods, request bodies, query strings, and WebSocket
upgrades. It rewrites matching upstream/root-relative redirects and root cookie
paths. It does not rewrite HTML, JavaScript, or backend security policies.

When mounting the portal below a URL prefix such as `/portal/`, configure the
front proxy to strip that prefix before forwarding and send
`X-Forwarded-Prefix: /portal`. Flask uses this trusted proxy header to generate
prefixed stylesheet, workspace, and service URLs. Do not accept this header from
untrusted direct clients.

## Backend Compatibility

Backends must generate URLs under their public prefix. Root-absolute assets or
fetch URLs such as `/static/app.js` will otherwise reach the portal, not the
backend. A generic reverse proxy cannot reliably rewrite every application.

For a Flask backend, configure Werkzeug `ProxyFix` with `x_prefix=1` (and
`x_host=1`, `x_proto=1` if needed), use `url_for` for links, and only trust the
single localhost Nginx proxy. Nginx strips `/services/evaluation/` before
forwarding and sends `X-Forwarded-Prefix: /services/evaluation`.

For Streamlit, configure `server.baseUrlPath` to the corresponding prefix
(for example `services/evaluation`) and remove the trailing slash from that
location's `proxy_pass` so Nginx preserves the path. For Gradio, configure its
`root_path` to the public prefix, retaining the supplied prefix-stripping proxy.
Consult the backend's version-specific documentation and verify assets, login,
uploads, redirects, and WebSockets after deploying.

Backends must allow embedding from this origin, for example with
`Content-Security-Policy: frame-ancestors 'self'` and, if present,
`X-Frame-Options: SAMEORIGIN`. A backend that sends `DENY` or
`frame-ancestors 'none'` cannot be framed; the configuration deliberately does
not strip these headers. The frame toolbar also offers opening the proxied
application directly in a new tab.

Only embed trusted applications. Same-origin frames can access the portal's
origin; they are not a security sandbox. Keep backend session cookie names
distinct. Put authentication and HTTPS on the public gateway before exposing
sensitive evaluation data: a private port does not make its proxied pages private.

## Configuration

Set environment variables before starting the app:

| Variable | Default | Purpose |
| --- | --- | --- |
| `HOST` | `127.0.0.1` | Private Flask bind address |
| `PORT` | `8081` | Private Flask port; also update Nginx if changed |
| `TOT4ES_PORT` | `5000` | Port label on the portal; update Nginx upstream separately |
| `HUMAN_EVALUATION_PORT` | `8011` | Port label on the portal; update Nginx upstream separately |
| `SYNTHETIC_DATASET_PORT` | `8022` | Port label on the portal; update Nginx upstream separately |

```sh
HOST=127.0.0.1 PORT=8081 python app.py
```

The old `SERVICE_SCHEME` option is no longer used. The browser always uses the
gateway's origin and protocol; Nginx can reach private HTTP backends even when
the public gateway is configured with HTTPS.

The built-in Flask server is for local development. For production, use a WSGI
server such as Gunicorn (`gunicorn --bind 127.0.0.1:8081 app:app`) behind Nginx.
Gunicorn is installed separately. Set an explicit public hostname in Nginx,
configure TLS, and limit allowed hosts for your deployment.

Fonts, icons, and the library photograph load from external services. Navigation
works without these assets; system fonts and a solid image background remain.

## LLM-Walk Service

Deploy both the updated portal and the sibling LLM-Walk repository to the server.
In LLM-Walk, use the Python environment that already runs its UI successfully;
install its dependencies first if needed. From its repository root:

```sh
sudo env SERVICE_USER="$USER" PYTHON_BIN="$PWD/.venv/bin/python" UI_PORT=8044 \
	bash scripts/deploy_ui.sh
```

Set `PYTHON_BIN` to your actual absolute interpreter path if different. The
installer creates `llm-walk-web.service`, binds the UI to `127.0.0.1:8044`, and
enables startup at boot. It does not install Python dependencies or LLM models.
The heuristic backend needs no running LLM; Ollama requires its local server and
model, and DICE requires its backend configuration. This is an experimental UI;
protect the public proxy with authentication and TLS before exposing model calls.

```sh
sudo systemctl restart llm-walk-web
sudo systemctl stop llm-walk-web
sudo systemctl start llm-walk-web
sudo systemctl status llm-walk-web --no-pager
sudo journalctl -u llm-walk-web -n 50 --no-pager
curl http://127.0.0.1:8044/api/datasets
```

For the existing Apache deployment, add these rules inside the active virtual
host, BEFORE the catch-all `ProxyPass "/"` rule:

```apache
ProxyPass        "/services/llm-walk/" "http://127.0.0.1:8044/"
ProxyPassReverse "/services/llm-walk/" "http://127.0.0.1:8044/"
```

Keep `ProxyPreserveHost On` so the UI's same-origin POST check sees the public
Host. The UI currently accepts HTTP origins; an HTTPS gateway needs corresponding
origin-validation support in the UI before simulation POSTs will work over HTTPS.
Keep backend port 8044 private. Run `sudo apache2ctl configtest` and reload Apache
only if it succeeds. Restart the portal to load its new LLM-Walk entry.

Open `/workspace/llm-walk/` on the public portal. LLM-Walk assets and API requests
use relative URLs, so retain the trailing slash in `/services/llm-walk/`.
The supplied Nginx config also includes this service if using Nginx instead.
`LLM_WALK_PORT` changes the portal label only; update the service and proxy
upstream separately if changing port 8044.

## Test Command

```sh
python -m unittest -v test_app
```