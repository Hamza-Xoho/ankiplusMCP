FROM python:3.13-slim-bookworm
ARG SOURCE_REVISION=uncommitted-dirty
ARG COMPANION_REVISION=uncommitted-dirty
LABEL org.opencontainers.image.revision=$SOURCE_REVISION org.ankiplus.companion.revision=$COMPANION_REVISION
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PLAYWRIGHT_BROWSERS_PATH=/opt/browsers QT_QPA_PLATFORM=offscreen HOME=/tmp/test-home
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr libatomic1 libglib2.0-0 libgl1 libegl1 libfontconfig1 libxkbcommon0 libdbus-1-3 libgssapi-krb5-2 && rm -rf /var/lib/apt/lists/*
COPY requirements.lock ./
RUN pip install --no-cache-dir 'aqt==26.9.2' && pip install --no-cache-dir -r requirements.lock && python -m playwright install --with-deps chromium && rm -rf /var/lib/apt/lists/*
RUN apt-get update && apt-get install -y --no-install-recommends libxtst6 libxi6 libxkbfile1 && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir --no-deps .
COPY tests/isolated/input/companion.ankiaddon /artifact/companion.ankiaddon
COPY tests/isolated/product_workflow.py tests/isolated/companion_stdio.py /artifact/
RUN python -m zipfile -e /artifact/companion.ankiaddon /artifact/addon && python -c "import pathlib,subprocess,sys; p=next(pathlib.Path('/artifact/addon/vendor/shared').glob('pydantic-*.dist-info')); subprocess.check_call([sys.executable,'-m','pip','install','--no-cache-dir','--target','/artifact/companion-runtime','pydantic=='+p.name[len('pydantic-'):-len('.dist-info')]])" && chmod -R a+rX /artifact /opt/browsers && useradd -u 1000 -M tester
USER 1000:1000
CMD ["python", "/artifact/product_workflow.py", "addon"]
