# Unoooooooo

A networked UNO game written in Python with a Pygame client and a TCP socket server.

## Requirements

- Python 3.11 or newer
- Up to four players on the same host or network

## Setup

Create and activate a virtual environment, then install the runtime dependency:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
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

The server and client currently connect over `127.0.0.1:65432`. Change `HOST` in
`Server/Server.py` and `SERVER_HOST` in `Client/UNO.py` to play across a network.

## Build the Windows client

Install the development dependencies and run PyInstaller from the client directory:

```powershell
python -m pip install -r requirements-dev.txt
Set-Location Client
pyinstaller UNO.spec
```

Generated `build/` and `dist/` directories are intentionally excluded from Git.

## Project layout

- `Client/UNO.py` — Pygame client and interface
- `Client/Cards/` — card artwork
- `Client/Additional_Assets/` — interface artwork and application icon
- `Client/UNO.spec` — PyInstaller configuration
- `Server/Server.py` — multiplayer game server

The older numbered “Working Step” snapshots were removed during repository cleanup;
their complete history remains available in Git commit `9622813`.
