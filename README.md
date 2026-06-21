# Unoooooooo

A networked UNO game written in Python with a Pygame client, an authoritative TCP
server, and optional Llama 3 players powered locally by Ollama.

## Requirements

- Python 3.11 or newer
- [Ollama](https://ollama.com/) for Llama players
- Up to four human or bot players on the same host or network

## Setup

Create and activate a virtual environment, then install the runtime dependency:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Install the default bot model once:

```powershell
ollama pull llama3.2:3b
```

## Run locally

Start the server from the repository root:

```powershell
python Server/Server.py
```

Then start one or more clients in separate terminals:

```powershell
python Client/UNO.py
```

By default, the server waits for two human clients and fills the other two seats
with Llama players. If Ollama or the configured model is unavailable, bots fall
back to a fast local strategy instead of stopping the game.

The server and client currently connect over `127.0.0.1:65432`. Set `UNO_HOST`
for the server and change `SERVER_HOST` in `Client/UNO.py` to play across a network.

## Bot configuration

The server reads these optional environment variables:

| Variable | Default | Purpose |
| --- | --- | --- |
| `UNO_HUMANS` | `2` | Number of human seats |
| `UNO_BOTS` | `2` | Number of server-side bot seats |
| `UNO_BOT_DELAY` | `0.8` | Seconds before each bot move |
| `OLLAMA_MODEL` | `llama3.2:3b` | Ollama model used by every bot |
| `OLLAMA_URL` | `http://127.0.0.1:11434` | Ollama API base URL |
| `OLLAMA_TIMEOUT` | `20` | Model request timeout in seconds |

For example, to use one human and three Llama players:

```powershell
$env:UNO_HUMANS = "1"
$env:UNO_BOTS = "3"
python Server/Server.py
```

## Build the Windows client

Install the development dependencies and run PyInstaller from the client directory:

```powershell
python -m pip install -r requirements-dev.txt
Set-Location Client
pyinstaller UNO.spec
```

Generated `build/` and `dist/` directories are intentionally excluded from Git.

## Project layout

- `Client/UNO.py` - Pygame client and interface
- `Client/Cards/` - card artwork
- `Client/Additional_Assets/` - interface artwork and application icon
- `Client/UNO.spec` - PyInstaller configuration
- `Server/Server.py` - multiplayer transport and bot orchestration
- `Server/game.py` - authoritative UNO rules and state
- `Server/bots.py` - Llama/Ollama decisions and strategic fallback
- `tests/` - rules, bot validation, and server protocol tests

The older numbered "Working Step" snapshots were removed during repository cleanup;
their complete history remains available in Git commit `9622813`.
