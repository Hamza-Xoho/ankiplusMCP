FROM python:3.14-slim
ARG SOURCE_REVISION=development-dirty
LABEL org.opencontainers.image.title="ankiplusmcp" org.opencontainers.image.revision=$SOURCE_REVISION
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PLAYWRIGHT_BROWSERS_PATH=/opt/browsers
WORKDIR /app
COPY requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock \
    && python -m playwright install --with-deps chromium \
    && apt-get update && apt-get install -y --no-install-recommends tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir --no-deps . \
    && useradd --uid 1000 --create-home app \
    && mkdir /workspaces /sources && chown app:app /workspaces \
    && chmod -R a+rX /opt/browsers
USER 1000:1000
ENTRYPOINT ["ankiplusmcp"]
CMD ["--workspace-root", "/workspaces", "--source-root", "/sources"]
