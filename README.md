# Docker Netmap

A tiny Python MVP that visualizes local Docker containers, networks, and published ports on a map.

## What it does

- Reads containers from your local Docker daemon
- Reads Docker networks and attached containers
- Builds a graph:
  - network nodes
  - container nodes
  - edges between containers and networks
- Shows published ports like `localhost:8080 -> container:80`
- Serves an interactive browser UI


<img width="1025" height="625" alt="dockermap1" src="https://github.com/user-attachments/assets/b1f2777a-0100-4d87-8401-7ae2e100b93a" />
<img width="1021" height="605" alt="dockermap2" src="https://github.com/user-attachments/assets/f0ccc860-b04b-4e57-bf0a-d8a12e81e6b4" />
<img width="1038" height="606" alt="dockermap3" src="https://github.com/user-attachments/assets/47a1c0d8-acae-441a-a795-bca1e3ac67de" />






## Install

Fork the repo and run with simple docker commands

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
