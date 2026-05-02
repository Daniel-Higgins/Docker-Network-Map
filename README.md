# Docker Netmap

A tiny Python MVP that visualizes local Docker containers, networks, and published ports.

## What it does

- Reads containers from your local Docker daemon
- Reads Docker networks and attached containers
- Builds a graph:
  - network nodes
  - container nodes
  - edges between containers and networks
- Shows published ports like `localhost:8080 -> container:80`
- Serves an interactive browser UI

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run locally

```bash
python -m docker_netmap
```

Open:

```text
http://localhost:8765
```

## Run with Docker

```bash
docker compose up --build
```

Open:

```text
http://localhost:8765
```

## Security note

The Docker socket is powerful. Mounting `/var/run/docker.sock` gives this app read access to Docker metadata and can be dangerous for untrusted code. Keep this local for now.
