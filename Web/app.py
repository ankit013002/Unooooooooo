"""FastAPI entrypoint for the browser-based UNO game."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from Web.rooms import RoomError, RoomManager, normalize_room_code


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOGGER = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = ROOT / "Web" / "static"
ASSET_DIR = ROOT / "assets"

app = FastAPI(title="Unoooooooo", version="2.0.0")
rooms = RoomManager()


class CreateRoomRequest(BaseModel):
    humanSeats: int = Field(default=2, ge=1, le=4)
    botSeats: int = Field(default=2, ge=0, le=3)


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/rooms")
async def create_room(settings: CreateRoomRequest) -> dict[str, int | str]:
    total = settings.humanSeats + settings.botSeats
    if not 2 <= total <= 4:
        raise HTTPException(status_code=422, detail="A room must have two to four total seats")
    room = await rooms.create(settings.humanSeats, settings.botSeats)
    return {
        "code": room.code,
        "humanSeats": room.human_seats,
        "botSeats": room.bot_seats,
    }


@app.get("/api/rooms/{code}")
async def room_status(code: str) -> dict[str, int | str]:
    room = rooms.get(code)
    if room is None:
        raise HTTPException(status_code=404, detail="Room not found")
    return {
        "code": room.code,
        "humanSeats": room.human_seats,
        "botSeats": room.bot_seats,
        "connectedHumans": sum(
            player.connected for player in room.players.values() if not player.bot
        ),
    }


@app.websocket("/ws/{code}")
async def game_socket(websocket: WebSocket, code: str, name: str = "Player", token: str | None = None) -> None:
    room = rooms.get(normalize_room_code(code))
    if room is None:
        await websocket.close(code=4404, reason="Room not found")
        return
    await websocket.accept()
    try:
        player = await room.connect(websocket, name, token)
    except RoomError as error:
        await websocket.send_json({"type": "error", "message": str(error)})
        await websocket.close(code=4409, reason=str(error))
        return

    LOGGER.info("%s joined room %s as player %s", player.name, room.code, player.player_id + 1)
    try:
        while True:
            payload = await websocket.receive_json()
            try:
                await room.handle_action(player.player_id, payload)
            except RoomError as error:
                await websocket.send_json({"type": "error", "message": str(error)})
    except WebSocketDisconnect:
        pass
    except Exception as error:
        LOGGER.warning("WebSocket error in room %s: %s", room.code, error)
    finally:
        await room.disconnect(player.player_id, websocket)


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/assets/cards", StaticFiles(directory=ASSET_DIR / "cards"), name="cards")
app.mount("/assets/ui", StaticFiles(directory=ASSET_DIR / "ui"), name="ui-assets")
