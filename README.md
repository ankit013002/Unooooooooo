# Unoooooooo

A private browser-based UNO game for two to four human and Llama players. One
Python process serves the website, room API, real-time WebSocket game server,
artwork, and server-side bots from your laptop.

## What you get

- Shareable four-character room codes
- One to four human seats and up to three Llama seats
- Responsive desktop and mobile browser interface
- Private hands and server-authoritative rules
- Automatic reconnection and paused games while a human reconnects
- Rematches without creating a new room
- Local Ollama integration with a reliable strategic fallback
- No client installation or desktop builds

## Setup

Python 3.11 or newer is recommended.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

For Llama players, install [Ollama](https://ollama.com/) and pull the default
model once:

```powershell
ollama pull llama3.2:3b
```

Bots automatically use the built-in strategic player whenever Ollama is not
running, so the game remains playable without it.

## Run the web app

```powershell
python run_web.py
```

Open `http://localhost:8000` on the host laptop. The launcher also prints the
LAN address to share with another device on the same Wi-Fi, such as:

```text
http://192.168.1.42:8000
```

If Windows asks, allow Python through the firewall on private networks. To use a
different port:

```powershell
$env:UNO_WEB_PORT = "8080"
python run_web.py
```

## Playing over the internet

The default configuration is intentionally LAN-only. To play from different
networks, forward the configured TCP port on the router or place a trusted HTTPS
tunnel/reverse proxy in front of the app. Do not expose the Ollama port; only the
UNO web port needs to be reachable.

## Bot configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `OLLAMA_MODEL` | `llama3.2:3b` | Ollama model used by Llama seats |
| `OLLAMA_URL` | `http://127.0.0.1:11434` | Ollama API base URL |
| `OLLAMA_TIMEOUT` | `20` | Model request timeout in seconds |
| `UNO_WEB_HOST` | `0.0.0.0` | Interface exposed by the web server |
| `UNO_WEB_PORT` | `8000` | Website and WebSocket port |

## Tests

```powershell
python -m unittest discover -v
```

Optional browser end-to-end test:

```powershell
npm install
npx playwright install chromium
npm run test:e2e
```

## Project layout

- `Web/app.py` - FastAPI routes, static files, and WebSocket endpoint
- `Web/rooms.py` - room lifecycle, reconnects, and bot orchestration
- `Web/static/` - browser interface
- `Server/game.py` - authoritative UNO rules
- `Server/bots.py` - Llama/Ollama decisions and strategic fallback
- `assets/` - card and interface artwork
- `tests/` - rules, bot, API, and room-flow tests
