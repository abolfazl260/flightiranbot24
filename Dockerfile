FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml .
COPY src ./src
COPY migrations ./migrations
COPY alembic.ini .
RUN pip install --no-cache-dir . && mkdir -p /data && chown nobody:nogroup /data
VOLUME ["/data"]
USER nobody
CMD ["flightiran"]
