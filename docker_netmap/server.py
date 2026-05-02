from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from docker_netmap.collector import build_docker_graph

APP_DIR = Path(__file__).parent
STATIC_DIR = APP_DIR / "static"

app = FastAPI(title="Docker Netmap", version="0.1.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/graph")
def graph(include_stopped: bool = True) -> dict:
    return build_docker_graph(include_stopped=include_stopped)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
