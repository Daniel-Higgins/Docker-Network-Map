FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY docker_netmap ./docker_netmap

EXPOSE 8765

CMD ["python", "-m", "docker_netmap"]
