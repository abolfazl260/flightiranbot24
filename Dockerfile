FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml .
COPY src ./src
# Same GitHub-managed airport guides as Android and Mini App.
COPY data/airports ./data/airports
# Lossless archive is server-side only; it is never a static asset or APK asset.
COPY data/experiences ./data/experiences
COPY scripts/manage_experiences.py ./scripts/manage_experiences.py
COPY migrations ./migrations
COPY alembic.ini .
RUN pip install --no-cache-dir . && mkdir -p /data && chown nobody:nogroup /data
VOLUME ["/data"]
USER nobody
CMD ["flightiran"]
