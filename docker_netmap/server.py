from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from docker_netmap.collector import build_docker_graph
import docker
from fastapi import HTTPException

APP_DIR = Path(__file__).parent
STATIC_DIR = APP_DIR / "static"

app = FastAPI(title="Docker Netmap", version="0.1.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")

#use json to build graph
@app.get("/api/graph")
def graph(include_stopped: bool = True) -> dict:
    return build_docker_graph(include_stopped=include_stopped)

@app.get("/api/containers/{container_name}/logs")
def container_logs(container_name: str, tail: int = 50) -> dict:
    try:
        client = docker.from_env()
        container = client.containers.get(container_name)

        logs = (
            container.logs(
                tail=tail,
                stdout=True,
                stderr=True,
            )
            .decode("utf-8", errors="replace")
            .splitlines()
        )

        return {
            "container": container_name,
            "logs": logs,
        }

    except docker.errors.NotFound:
        raise HTTPException(status_code=404, detail="Container not found")

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

#simple health check
@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
